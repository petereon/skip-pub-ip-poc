use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use mainline::{Dht, Id};
use mainline::common::hash_immutable;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use bytes::Bytes;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct PeerInfo {
    #[pyo3(get)]
    pub peer_id: String,
    #[pyo3(get)]
    pub ws_url: String,
    #[pyo3(get)]
    pub port: u16,
}

#[pymethods]
impl PeerInfo {
    #[new]
    fn new(peer_id: String, ws_url: String, port: u16) -> Self {
        Self { peer_id, ws_url, port }
    }
}

#[pyclass]
struct BTDht {
    dht: Arc<Mutex<Option<Dht>>>,
    services: Arc<Mutex<HashMap<String, PeerInfo>>>,
}

#[pymethods]
impl BTDht {
    #[new]
    fn new() -> Self {
        Self {
            dht: Arc::new(Mutex::new(None)),
            services: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    fn start<'py>(&mut self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let dht_arc = self.dht.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let dht = Dht::default();
            let mut dht_lock = dht_arc.lock().unwrap();
            *dht_lock = Some(dht);
            Ok(())
        })
    }

    fn bootstrap<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        pyo3_asyncio::tokio::future_into_py(py, async move {
            // DHT bootstraps automatically when created
            println!("✅ DHT initialized with default bootstrap nodes!");
            Ok(())
        })
    }

    fn register_service<'py>(&self, py: Python<'py>, service_key: String, ws_url: String, port: u16) -> PyResult<&'py PyAny> {
        let peer_id = format!("py-ws-{}", uuid::Uuid::new_v4());
        let peer_info = PeerInfo { peer_id: peer_id.clone(), ws_url: ws_url.clone(), port };

        // Store locally
        self.services.lock().unwrap().insert(service_key.clone(), peer_info.clone());

        // Announce to BitTorrent DHT
        let value = bincode::serialize(&peer_info)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialization failed: {:?}", e)))?;

        let dht_arc = self.dht.clone();
        let service_key_clone = service_key.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let dht = dht_arc.lock().unwrap();
            let dht = dht.as_ref().ok_or_else(|| PyRuntimeError::new_err("DHT not started"))?;

            let bytes_value = Bytes::from(value);
            let result = dht.put_immutable(bytes_value)
                .map_err(|e| PyRuntimeError::new_err(format!("Store failed: {:?}", e)))?;

            let actual_hash = result.target();
            let hash_str = format!("{:?}", actual_hash);

            println!("✅ Registered {} -> {} in BitTorrent DHT", service_key_clone, ws_url);
            println!("   Hash: {}", hash_str);
            println!("   Stored at {} nodes", result.stored_at().len());
            println!("\n   📋 Copy this hash to use in client:");
            println!("   {}", hash_str);

            Ok(Python::with_gil(|py| hash_str.into_py(py)))
        })
    }

    fn find_service<'py>(&self, py: Python<'py>, service_key: String) -> PyResult<&'py PyAny> {
        let dht_arc = self.dht.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let dht = dht_arc.lock().unwrap();
            let dht = dht.as_ref().ok_or_else(|| PyRuntimeError::new_err("DHT not started"))?;

            // Compute the same deterministic hash from service_key
            let key_hash = hash_immutable(service_key.as_bytes());
            let target = Id::from_bytes(key_hash)
                .map_err(|e| PyRuntimeError::new_err(format!("Invalid hash: {:?}", e)))?;

            println!("🔍 Searching for {} (target: {:?})...", service_key, target);

            // Retrieve from DHT
            let mut response = dht.get_immutable(target);

            // Get first successful response
            for res in &mut response {
                if let Ok(peer_info) = bincode::deserialize::<PeerInfo>(&res.value) {
                    println!("✅ Found {} -> {} from DHT node {:?}", service_key, peer_info.ws_url, res.from);
                    return Ok(Python::with_gil(|py| peer_info.ws_url.into_py(py)));
                }
            }

            println!("❌ Service '{}' not found in DHT", service_key);
            // No valid responses
            Ok(Python::with_gil(|py| py.None()))
        })
    }

    fn find_by_hash<'py>(&self, py: Python<'py>, hash_str: String) -> PyResult<&'py PyAny> {
        let dht_arc = self.dht.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let dht = dht_arc.lock().unwrap();
            let dht = dht.as_ref().ok_or_else(|| PyRuntimeError::new_err("DHT not started"))?;

            // Parse the hash string - format is "Id(hexstring)"
            let hex_str = hash_str.trim_start_matches("Id(").trim_end_matches(")");
            let hash_bytes = hex::decode(hex_str)
                .map_err(|e| PyRuntimeError::new_err(format!("Invalid hash format: {:?}", e)))?;

            if hash_bytes.len() != 20 {
                return Err(PyRuntimeError::new_err("Hash must be 20 bytes (SHA1)"));
            }

            let mut arr = [0u8; 20];
            arr.copy_from_slice(&hash_bytes);
            let target = Id::from_bytes(arr)
                .map_err(|e| PyRuntimeError::new_err(format!("Invalid ID: {:?}", e)))?;

            println!("🔍 Searching by hash {:?}...", target);

            // Retrieve from DHT
            let mut response = dht.get_immutable(target);

            // Get first successful response
            for res in &mut response {
                if let Ok(peer_info) = bincode::deserialize::<PeerInfo>(&res.value) {
                    println!("✅ Found {} from DHT node {:?}", peer_info.ws_url, res.from);
                    return Ok(Python::with_gil(|py| peer_info.ws_url.into_py(py)));
                }
            }

            println!("❌ No data found at this hash");
            Ok(Python::with_gil(|py| py.None()))
        })
    }

    fn list_services(&self) -> Vec<(String, String)> {
        self.services.lock().unwrap()
            .iter()
            .map(|(k, v)| (k.clone(), v.ws_url.clone()))
            .collect()
    }
}

#[pymodule]
fn btdht_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<BTDht>()?;
    m.add_class::<PeerInfo>()?;
    Ok(())
}
