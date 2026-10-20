# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Changes in releases up to v0.10.6 are listed in the [GitHub releases](https://github.com/input-output-hk/cardano-clusterlib-py/releases).

## [0.10.9]

- Dijkstra sub-transaction building, signing, and IDs through `ClusterLib.g_sub_transaction`.
- Reusable `TxGuard` and `RequiredTopLevelGuard` records with shared guard argument formatting. Normal transaction guard support awaits a CLI fix.
- Ordered embedding in `build_raw_tx_bare` and batch balancing in `build_raw_tx`, `calculate_tx_fee`, and `send_tx` using `SignedSubTx` records.
- File-only embedding through `build_raw_tx(sub_transaction_files=...)` with explicit inputs and manually balanced outputs, without automatic input selection or change.
- Explicit parent `collateral_txins` for raw transactions, including batches with Plutus sub-transactions.
- General reserved-input exclusion in `collect_data_for_build` and the shared input-selection helper, including for transactions without sub-transactions. An explicitly empty source UTxO cache no longer triggers a fallback query.

## [0.10.7]

### Added

- `ClusterLib.alonzo_genesis` and `ClusterLib.alonzo_genesis_json` with the Alonzo genesis, loaded when the command era is Alonzo or newer.
- `ClusterLib.dijkstra_genesis` and `ClusterLib.dijkstra_genesis_json` with the Dijkstra genesis, loaded when the command era is Dijkstra or newer.
- `ClusterLib.load_full_genesis()` for loading the complete Shelley genesis. The genesis is read from the file on each call and is not cached.

### Changed

- **Breaking:** `ClusterLib.genesis` no longer contains the Shelley genesis keys that can be huge with many injected pools or UTxOs: `initialFunds`, `staking`, `extraConfig.initialFunds`, `extraConfig.stakeCredentials` and `extraConfig.stakePools` (see `clusterlib_helpers.GENESIS_BULKY_KEYS`). Use `ClusterLib.load_full_genesis()` when these keys are needed.
- The private `clusterlib_helpers._find_conway_genesis_json` was replaced by the generic `clusterlib_helpers._find_era_genesis_json`.

[0.10.7]: https://github.com/input-output-hk/cardano-clusterlib-py/compare/v0.10.6...v0.10.7
