# cgwt

CLI tool to manage git worktrees, with a behavior that is modifiable with a configuration file.

## Install

```sh
uv tool install cgwt
```

`pipx install cgwt` works too. PyPI serves prebuilt wheels for Linux, macOS, and Windows. Other platforms build from the source distribution and need a Rust toolchain.

## Development

cgwt is a Rust crate. [maturin](https://www.maturin.rs) packages the binary into Python wheels.

```sh
cargo test
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo llvm-cov --fail-under-lines 95 --fail-under-regions 90
maturin build --release --out dist
```

Coverage needs [cargo-llvm-cov](https://github.com/taiki-e/cargo-llvm-cov).

## Release

The version lives in `Cargo.toml`. To release, bump it, commit, and push a matching `v*` tag. The release workflow builds the wheels and publishes them to PyPI.
