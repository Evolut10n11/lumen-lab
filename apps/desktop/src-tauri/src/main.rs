use std::env;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::Manager;

fn bundled_engine_candidates(app: &tauri::AppHandle) -> Vec<PathBuf> {
    let mut candidates = Vec::new();

    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("resources").join("lumen-engine.exe"));
        candidates.push(resource_dir.join("lumen-engine.exe"));
    }

    if let Ok(current_exe) = env::current_exe() {
        if let Some(exe_dir) = current_exe.parent() {
            candidates.push(exe_dir.join("resources").join("lumen-engine.exe"));
            candidates.push(exe_dir.join("lumen-engine.exe"));
        }
    }

    candidates.sort();
    candidates.dedup();
    candidates
}

fn bundled_engine_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    bundled_engine_candidates(app)
        .into_iter()
        .find(|candidate| candidate.is_file())
}

fn engine_command(app: &tauri::AppHandle) -> Result<(Command, String), String> {
    if let Ok(python) = env::var("LUMEN_PYTHON") {
        let mut command = Command::new(&python);
        command.arg("-m").arg("lumen_lab.desktop_bridge");
        return Ok((command, format!("Python override '{python}'")));
    }

    if let Some(engine) = bundled_engine_path(app) {
        let label = engine.display().to_string();
        return Ok((Command::new(engine), label));
    }

    if cfg!(debug_assertions) {
        let python = "python".to_string();
        let mut command = Command::new(&python);
        command.arg("-m").arg("lumen_lab.desktop_bridge");
        return Ok((command, "development Python engine".to_string()));
    }

    let searched = bundled_engine_candidates(app)
        .into_iter()
        .map(|path| path.display().to_string())
        .collect::<Vec<_>>()
        .join("; ");

    Err(format!(
        "Lumen's bundled engine is missing from this installation. Searched: {searched}"
    ))
}

#[tauri::command]
fn lumen_request(app: tauri::AppHandle, request: String) -> Result<String, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("could not resolve app data directory: {error}"))?;

    fs::create_dir_all(&data_dir)
        .map_err(|error| format!("could not create app data directory: {error}"))?;

    let (mut command, engine_label) = engine_command(&app)?;

    // The desktop bridge speaks JSON over stdio. On Windows, Python can otherwise
    // inherit the active ANSI code page while Tauri expects UTF-8.
    command
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1");

    let mut child = command
        .current_dir(&data_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("could not start Lumen engine ({engine_label}): {error}"))?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(request.as_bytes())
            .map_err(|error| format!("could not send request to Lumen engine: {error}"))?;
    }

    let output = child
        .wait_with_output()
        .map_err(|error| format!("Lumen engine did not finish correctly ({engine_label}): {error}"))?;

    // UTF-8 is the protocol. Keep a lossy fallback so a localized Windows runtime
    // message cannot make the whole desktop app fail before we can show diagnostics.
    let stdout = match String::from_utf8(output.stdout) {
        Ok(stdout) => stdout,
        Err(error) => String::from_utf8_lossy(error.as_bytes()).into_owned(),
    };

    if !stdout.trim().is_empty() {
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

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![lumen_request])
        .run(tauri::generate_context!())
        .expect("error while running Lumen desktop application");
}
