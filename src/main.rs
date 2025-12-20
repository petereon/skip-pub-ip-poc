// P2P Node: Simple send/listen API for bidirectional byte-stream messaging
// Transport-agnostic: handles raw bytes, Python handles JSON encoding/decoding

use anyhow::Result;
use clap::Parser;
use futures::StreamExt;
use libp2p::{
    dcutr, identify, kad, noise, ping, relay,
    swarm::{NetworkBehaviour, SwarmEvent},
    PeerId, Swarm,
};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::{mpsc, RwLock};
use tracing::{error, info, warn};

#[derive(Parser, Debug)]
#[command(name = "p2p-node")]
#[command(about = "P2P node with simple send/listen API")]
struct Args {
    /// Service name to register/lookup in DHT
    #[arg(long, default_value = "myapi:v1")]
    service: String,

    /// Mode: server or client
    #[arg(long)]
    mode: String,

    /// Port for stdin/stdout interface
    #[arg(long, default_value = "0")]
    port: u16,
}

// Network behaviour
#[derive(NetworkBehaviour)]
struct P2PBehaviour {
    relay: relay::client::Behaviour,
    ping: ping::Behaviour,
    identify: identify::Behaviour,
    kad: kad::Behaviour<kad::store::MemoryStore>,
    dcutr: dcutr::Behaviour,
}

// Shared state - transport layer only handles raw bytes
struct NodeState {
    peers: Arc<RwLock<HashMap<PeerId, mpsc::Sender<Vec<u8>>>>>,
    _service_key: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("p2p_node=info".parse()?)
                .add_directive("libp2p=info".parse()?),
        )
        .init();

    info!("🚀 Starting P2P Node in {} mode", args.mode);
    info!("📡 Service: {}", args.service);

    // Create keypair
    let local_key = libp2p::identity::Keypair::generate_ed25519();
    let local_peer_id = PeerId::from(local_key.public());
    info!("🆔 PeerId: {}", local_peer_id);

    // Build swarm with relay support
    let mut swarm = libp2p::SwarmBuilder::with_existing_identity(local_key.clone())
        .with_async_std()
        .with_tcp(
            libp2p::tcp::Config::default(),
            noise::Config::new,
            libp2p::yamux::Config::default,
        )?
        .with_quic()
        .with_relay_client(noise::Config::new, libp2p::yamux::Config::default)?
        .with_behaviour(|keypair, relay_behaviour| {
            let peer_id = keypair.public().to_peer_id();

            // Create Kademlia behaviour
            let mut kad_config = kad::Config::default();
            kad_config.set_query_timeout(Duration::from_secs(300));
            let store = kad::store::MemoryStore::new(peer_id);
            let mut kad = kad::Behaviour::with_config(peer_id, store, kad_config);
            kad.set_mode(Some(kad::Mode::Server));

            P2PBehaviour {
                relay: relay_behaviour,
                ping: ping::Behaviour::new(ping::Config::new()),
                identify: identify::Behaviour::new(identify::Config::new(
                    "/p2p-simple/0.1.0".to_string(),
                    keypair.public(),
                )),
                kad,
                dcutr: dcutr::Behaviour::new(peer_id),
            }
        })?
        .with_swarm_config(|c| c.with_idle_connection_timeout(Duration::from_secs(60)))
        .build();

    // Listen on all interfaces
    swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse()?)?;
    swarm.listen_on("/ip4/0.0.0.0/udp/0/quic-v1".parse()?)?;

    // Add IPFS bootstrap nodes to join the global DHT
    info!("🌐 Adding bootstrap nodes...");
    let bootstrap_nodes = vec![
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN",
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmQCU2EcMqAqQPR2i9bChDtGNJchTbq5TbXJJ16u19uLTa",
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb",
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmcZf59bWwK5XFi76CZX8cbJ4BhTzzA3gU1ZjYZcYW3dwt",
    ];

    for addr in bootstrap_nodes {
        if let Ok(multiaddr) = addr.parse::<libp2p::Multiaddr>() {
            if let Some(libp2p::multiaddr::Protocol::P2p(peer_id)) =
                multiaddr.iter().find(|p| matches!(p, libp2p::multiaddr::Protocol::P2p(_)))
            {
                let peer_id = PeerId::from_multihash(peer_id.into()).expect("valid peer id");
                swarm.behaviour_mut().kad.add_address(&peer_id, multiaddr);
                info!("Added bootstrap peer: {}", peer_id);
            }
        }
    }

    // Bootstrap to DHT
    info!("🌐 Bootstrapping to DHT...");
    if let Err(e) = swarm.behaviour_mut().kad.bootstrap() {
        warn!("Kademlia bootstrap failed: {}", e);
    }

    let state = Arc::new(NodeState {
        peers: Arc::new(RwLock::new(HashMap::new())),
        _service_key: args.service.clone(),
    });

    // Handle mode-specific setup
    let service_key = service_key(&args.service);
    let mut registered = false;
    let mut discovered_peer: Option<PeerId> = None;
    let mut bootstrapped = false;

    // For client: periodically retry get_providers until we find a server.
    let (lookup_tx, mut lookup_rx) = mpsc::channel::<()>(1);
    if args.mode == "client" {
        let lookup_tx_clone = lookup_tx.clone();
        tokio::spawn(async move {
            // initial delay to give server time to come up and announce
            let mut interval = tokio::time::interval(Duration::from_secs(10));
            loop {
                interval.tick().await;
                if lookup_tx_clone.send(()).await.is_err() {
                    break;
                }
            }
        });
    }

    // Channel for stdin commands
    let (stdin_tx, mut stdin_rx) = mpsc::channel::<String>(100);

    // Spawn stdin reader
    tokio::spawn(async move {
        let stdin = tokio::io::stdin();
        let reader = BufReader::new(stdin);
        let mut lines = reader.lines();

        while let Ok(Some(line)) = lines.next_line().await {
            if stdin_tx.send(line).await.is_err() {
                break;
            }
        }
    });

    info!("✅ Ready! Commands:");
    info!("   send <peer_id> <message>  - Send message to peer");
    info!("   list                      - List connected peers");

    // Main event loop
    loop {
        tokio::select! {
            event = swarm.select_next_some() => {
                match event {
                    SwarmEvent::NewListenAddr { address, .. } => {
                        info!("🎧 Listening on {}", address);
                    }

                    SwarmEvent::Behaviour(P2PBehaviourEvent::Identify(
                        identify::Event::Received { peer_id, info },
                    )) => {
                        info!("🔍 Identified peer {}", peer_id);
                        for addr in info.listen_addrs {
                            swarm.behaviour_mut().kad.add_address(&peer_id, addr);
                        }
                    }

                    SwarmEvent::Behaviour(P2PBehaviourEvent::Kad(
                        kad::Event::OutboundQueryProgressed { result, .. },
                    )) => match result {
                        kad::QueryResult::Bootstrap(Ok(_)) => {
                            info!("✅ Bootstrap successful");
                            bootstrapped = true;
                            // Once bootstrapped, server can safely announce.
                            if args.mode == "server" && !registered {
                                info!("📣 Registering service '{}' in DHT", args.service);
                                if let Err(e) = swarm.behaviour_mut().kad.start_providing(service_key.clone()) {
                                    error!("Failed to start providing: {}", e);
                                } else {
                                    registered = true;
                                    info!("✅ Service '{}' is now being provided", args.service);
                                }
                            }
                        }
                        kad::QueryResult::GetProviders(Ok(kad::GetProvidersOk::FoundProviders {
                            providers, ..
                        })) => {
                            if !providers.is_empty() {
                                let peer_id = *providers.iter().next().unwrap();
                                info!("✅ Found service provider: {}", peer_id);
                                discovered_peer = Some(peer_id);
                                if let Err(e) = swarm.dial(peer_id) {
                                    error!("Failed to dial: {}", e);
                                }
                            } else {
                                warn!("No providers returned in FoundProviders");
                            }
                        }
                        kad::QueryResult::GetProviders(Ok(kad::GetProvidersOk::FinishedWithNoAdditionalRecord { .. })) => {
                            // This is the "no providers yet" case seen in the file-sharing example [web:21].
                            warn!("No providers found yet for service key, will retry...");
                        }
                        _ => {}
                    },

                    SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                        info!("🔗 Connected to {}", peer_id);
                    }

                    _ => {}
                }
            }

            // periodic provider lookup in client mode
            Some(_) = lookup_rx.recv(), if args.mode == "client" && discovered_peer.is_none() && bootstrapped => {
                info!("🔍 Looking up service providers for '{}'", args.service);
                swarm.behaviour_mut().kad.get_providers(service_key.clone());
            }

            Some(cmd) = stdin_rx.recv() => {
                handle_command(&cmd, &mut swarm, &state, &local_peer_id).await;
            }
        }
    }
}

async fn handle_command(
    cmd: &str,
    _swarm: &mut Swarm<P2PBehaviour>,
    state: &Arc<NodeState>,
    _local_peer_id: &PeerId,
) {
    let parts: Vec<&str> = cmd.trim().split_whitespace().collect();

    match parts.first().map(|s| *s) {
        Some("send") if parts.len() >= 3 => {
            let peer_str = parts[1];
            let message = parts[2..].join(" ");

            // For demo, just print - actual stream handling would go here
            info!("📤 Would send to {}: {}", peer_str, message);
        }
        Some("list") => {
            let peers = state.peers.read().await;
            info!("📋 Connected peers: {}", peers.len());
            for peer in peers.keys() {
                println!("{}", peer);
            }
        }
        _ => {
            info!("❓ Unknown command. Try: send <peer_id> <msg> | list");
        }
    }
}

fn service_key(service_name: &str) -> kad::RecordKey {
    kad::RecordKey::new(&format!("service:{}", service_name))
}
