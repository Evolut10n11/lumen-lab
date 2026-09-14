use std::env;
use std::fs;
use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, ExitStatus, Stdio};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};
use tauri::path::BaseDirectory;
use tauri::Manager;
use tokio::sync::Mutex;

const ENGINE_TIMEOUT_SECONDS: u64 = 45;
const ENGINE_POLL_INTERVAL_MS: u64 = 20;
static ENGINE_REQUEST_LOCK: Mutex<()> = Mutex::const_new(());

struct EngineOutput {
    status: ExitStatus,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    elapsed: Duration,
}

fn spawn_reader<R>(mut stream: R) -> JoinHandle<std::io::Result<Vec<u8>>>
where
    R: Read + Send + 'static,
{
    thread::spawn(move || {
        let mut data = Vec::new();
        stream.read_to_end(&mut data)?;
        Ok(data)
    })
}

fn spawn_writer(
    mut stream: ChildStdin,
    request: Vec<u8>,
) -> JoinHandle<std::io::Result<()>> {
    thread::spawn(move || {
        stream.write_all(&request)?;
        stream.flush()
    })
}

fn join_reader(
    handle: JoinHandle<std::io::Result<Vec<u8>>>,
    stream_name: &str,
) -> Result<Vec<u8>, String> {
    handle
        .join()
        .map_err(|_| format!("Lumen engine {stream_name} reader stopped unexpectedly"))?
        .map_err(|error| format!("could not read Lumen engine {stream_name}: {error}"))
}

fn join_writer(handle: JoinHandle<std::io::Result<()>>) -> Result<(), String> {
    handle
        .join()
        .map_err(|_| "Lumen engine stdin writer stopped unexpectedly".to_string())?
        .map_err(|error| format!("could not send request to Lumen engine: {error}"))
}

fn collect_engine_output(
    mut child: Child,
    engine_label: &str,
    started: Instant,
) -> Result<EngineOutput, String> {
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Lumen engine stdout pipe is unavailable".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "Lumen engine stderr pipe is unavailable".to_string())?;
    let stdout_reader = spawn_reader(stdout);
    let stderr_reader = spawn_reader(stderr);

    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if started.elapsed() >= Duration::from_secs(ENGINE_TIMEOUT_SECONDS) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = join_reader(stdout_reader, "stdout");
                let stderr = join_reader(stderr_reader, "stderr").unwrap_or_default();
                let diagnostic = String::from_utf8_lossy(&stderr);
                let detail = diagnostic.trim();
                return Err(if detail.is_empty() {
                    format!(
                        "Lumen engine timed out after {ENGINE_TIMEOUT_SECONDS} seconds ({engine_label})"
                    )
                } else {
                    format!(
                        "Lumen engine timed out after {ENGINE_TIMEOUT_SECONDS} seconds ({engine_label}): {detail}"
                    )
                });
            }
            Ok(None) => thread::sleep(Duration::from_millis(ENGINE_POLL_INTERVAL_MS)),
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = join_reader(stdout_reader, "stdout");
                let _ = join_reader(stderr_reader, "stderr");
                return Err(format!(
                    "could not monitor Lumen engine ({engine_label}): {error}"
                ));
            }
        }
    };

    Ok(EngineOutput {
        status,
        stdout: join_reader(stdout_reader, "stdout")?,
        stderr: join_reader(stderr_reader, "stderr")?,
        elapsed: started.elapsed(),
    })
}

fn bundled_engine_candidates(app: &tauri::AppHandle) -> Vec<PathBuf> {
    let mut candidates = Vec::new();

    for relative in ["lumen-engine.exe", "resources/lumen-engine.exe"] {
        if let Ok(path) = app.path().resolve(relative, BaseDirectory::Resource) {
            candidates.push(path);
        }
    }

    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("lumen-engine.exe"));
        candidates.push(resource_dir.join("resources").join("lumen-engine.exe"));
    }

    if let Ok(current_exe) = env::current_exe() {
        if let Some(parent) = current_exe.parent() {
            candidates.push(parent.join("lumen-engine.exe"));
            candidates.push(parent.join("resources").join("lumen-engine.exe"));
        }
    }

    candidates.sort();
    candidates.dedup();
    candidates
}

fn bundled_engine_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let candidates = bundled_engine_candidates(app);
    if let Some(path) = candidates.iter().find(|path| path.is_file()) {
        return Ok(path.clone());
    }

    let checked = candidates
        .iter()
        .map(|path| path.display().to_string())
        .collect::<Vec<_>>()
        .join("; ");
    Err(format!(
        "Lumen's bundled engine is missing from this installation. Checked: {checked}. Reinstall Lumen and try again."
    ))
}

fn engine_command(app: &tauri::AppHandle) -> Result<(Command, String), String> {
    if let Ok(python) = env::var("LUMEN_PYTHON") {
        let mut command = Command::new(&python);
        command.arg("-m").arg("lumen_lab.packaged_engine");
        return Ok((command, format!("Python override '{python}'")));
    }

    if cfg!(debug_assertions) {
        if let Ok(engine) = bundled_engine_path(app) {
            let label = engine.display().to_string();
            return Ok((Command::new(engine), label));
        }

        let python = "python".to_string();
        let mut command = Command::new(&python);
        command.arg("-m").arg("lumen_lab.packaged_engine");
        return Ok((command, "development Python engine".to_string()));
    }

    let engine = bundled_engine_path(app)?;
    let label = engine.display().to_string();
    Ok((Command::new(engine), label))
}

fn lumen_request_blocking(app: tauri::AppHandle, request: String) -> Result<String, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("could not resolve app data directory: {error}"))?;

    fs::create_dir_all(&data_dir)
        .map_err(|error| format!("could not create app data directory: {error}"))?;

    let (mut command, engine_label) = engine_command(&app)?;

    // Helpful for development interpreters, but NOT the packaged transport
    // contract: PyInstaller can ignore Python environment configuration.
    // packaged_engine owns explicit UTF-8 bytes on both sides of the pipe.
    command
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1");

    let started = Instant::now();
    let mut child = command
        .current_dir(&data_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("could not start Lumen engine ({engine_label}): {error}"))?;

    let stdin = child
        .stdin
        .take()
        .ok_or_else(|| "Lumen engine stdin pipe is unavailable".to_string())?;
    let stdin_writer = spawn_writer(stdin, request.into_bytes());
    let output = match collect_engine_output(child, &engine_label, started) {
        Ok(output) => output,
        Err(error) => {
            let _ = join_writer(stdin_writer);
            return Err(error);
        }
    };
    join_writer(stdin_writer)?;

    // Never turn invalid protocol bytes into replacement characters and call
    // that success. Lossy decoding is reserved for human-readable stderr below.
    let stdout = String::from_utf8(output.stdout).map_err(|error| {
        format!(
            "Lumen engine returned invalid UTF-8 at byte {} ({engine_label}). No response text was substituted.",
            error.utf8_error().valid_up_to()
        )
    })?;

    if !stdout.trim().is_empty() {
        if env::var_os("LUMEN_LOG_TIMINGS").is_some() {
            eprintln!(
                "Lumen engine request completed in {} ms ({engine_label})",
                output.elapsed.as_millis()
            );
        }
        return Ok(stdout);
    }

    let stderr = String::from_utf8_lossy(&output.stderr);
    Err(if stderr.trim().is_empty() {
        format!(
            "Lumen engine returned no response ({engine_label}, exit code: {:?})",
            output.status.code()
        )
    } else {
        format!(
            "Lumen engine failed ({engine_label}, exit code: {:?}): {}",
            output.status.code(),
            stderr.trim()
        )
    })
}

#[tauri::command]
async fn lumen_request(app: tauri::AppHandle, request: String) -> Result<String, String> {
    let _request_guard = ENGINE_REQUEST_LOCK.lock().await;
    tauri::async_runtime::spawn_blocking(move || lumen_request_blocking(app, request))
        .await
        .map_err(|error| format!("Lumen engine worker stopped unexpectedly: {error}"))?
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![lumen_request])
        .run(tauri::generate_context!())
        .expect("error while running Lumen desktop application");
}
