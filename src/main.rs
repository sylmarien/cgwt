use std::process::ExitCode;

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    if arguments == ["--version"] {
        println!("cgwt {}", env!("CARGO_PKG_VERSION"));
        ExitCode::SUCCESS
    } else {
        eprintln!("usage: cgwt --version");
        ExitCode::from(2)
    }
}
