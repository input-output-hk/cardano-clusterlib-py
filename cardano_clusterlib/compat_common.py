"""Generic reusable classes for cardano-cli `compatible` commands."""

import pathlib as pl

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import txtools
from cardano_clusterlib import types as itp


class StakeAddressGroup:
    """Compatible stake-address commands for Alonzo / Mary / Babbage eras."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "stake-address")
        self.era = era

    def _resolve_stake_key_args(
        self,
        *,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
    ) -> list[str]:
        """Resolve stake key CLI arguments for compatible-era commands.

        Args:
            stake_vkey: A stake verification key (optional).
            stake_vkey_file: A path to stake verification key file (optional).
            stake_key_hash: A stake key hash (optional).
            stake_script_file: A path to stake script file (optional).
            stake_address: A stake address (optional).

        Returns:
            list[str]: A list of CLI arguments for stake key identification.

        Raises:
            ValueError: If none of the stake identification arguments are provided.
        """
        if stake_vkey:
            return ["--stake-verification-key", stake_vkey]

        if stake_vkey_file:
            return ["--stake-verification-key-file", str(stake_vkey_file)]

        if stake_key_hash:
            return ["--stake-key-hash", stake_key_hash]

        if stake_script_file:
            return ["--stake-script-file", str(stake_script_file)]

        if stake_address:
            return ["--stake-address", stake_address]

        message = (
            "One of stake_vkey, stake_vkey_file, stake_key_hash, "
            "stake_script_file or stake_address must be provided."
        )
        raise ValueError(message)

    def gen_registration_cert(
        self,
        *,
        name: str,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address registration certificate for compatible eras.

        Args:
            name: A name for the certificate file.
            stake_vkey: A stake verification key (optional).
            stake_vkey_file: A path to stake verification key file (optional).
            stake_key_hash: A stake key hash (optional).
            stake_script_file: A path to stake script file (optional).
            stake_address: A stake address (optional).
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_stake_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        stake_args = self._resolve_stake_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        cmd = [
            *self._base,
            "registration-certificate",
            *stake_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def gen_delegation_cert(
        self,
        *,
        name: str,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
        stake_pool_vkey: str = "",
        cold_vkey_file: itp.FileType | None = None,
        stake_pool_id: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake delegation certificate for compatible eras.

        Args:
            name: A name for the certificate file.
            stake_vkey: A stake verification key (optional).
            stake_vkey_file: A path to stake verification key file (optional).
            stake_key_hash: A stake key hash (optional).
            stake_script_file: A path to stake script file (optional).
            stake_address: A stake address (optional).
            stake_pool_vkey: A stake pool verification key (optional).
            cold_vkey_file: A path to cold verification key file (optional).
            stake_pool_id: A stake pool ID (optional).
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.

        Raises:
            ValueError: If none of the stake identification arguments are provided, or
                if none of the pool identification arguments are provided.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_stake_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        # Stake identification:
        stake_args = self._resolve_stake_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        # Pool identification:
        if stake_pool_vkey:
            pool_args = ["--stake-pool-verification-key", stake_pool_vkey]
        elif cold_vkey_file:
            pool_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif stake_pool_id:
            pool_args = ["--stake-pool-id", stake_pool_id]
        else:
            message = (
                "One of stake_pool_vkey, cold_vkey_file or stake_pool_id "
                "must be provided for delegation."
            )
            raise ValueError(message)

        cmd = [
            *self._base,
            "stake-delegation-certificate",
            *stake_args,
            *pool_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def __repr__(self) -> str:
        return f"<StakeAddressGroup era={self.era} base={self._base}>"


class StakePoolGroup:
    """Compatible stake-pool group for all compatible eras."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "stake-pool")
        self.era = era

    def gen_registration_cert(
        self,
        *,
        name: str,
        pool_data: structs.PoolData,
        cold_vkey_file: itp.FileType,
        vrf_vkey_file: itp.FileType,
        owner_stake_vkey_files: list[itp.FileType],
        reward_account_vkey_file: itp.FileType | None = None,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake pool registration certificate for compatible eras.

        Args:
            name: A name for the certificate file.
            pool_data: A `structs.PoolData` data container with pool parameters.
            cold_vkey_file: A path to cold verification key file.
            vrf_vkey_file: A path to VRF verification key file.
            owner_stake_vkey_files: A list of paths to owner stake verification key files.
            reward_account_vkey_file: A path to reward account verification key file (optional).
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_pool_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        relay_args: list[str] = []

        if pool_data.pool_relay_dns:
            relay_args.extend(["--single-host-pool-relay", pool_data.pool_relay_dns])

        if pool_data.pool_relay_ipv4:
            relay_args.extend(["--pool-relay-ipv4", pool_data.pool_relay_ipv4])

        if pool_data.pool_relay_ipv6:
            relay_args.extend(["--pool-relay-ipv6", pool_data.pool_relay_ipv6])

        if pool_data.pool_relay_port:
            relay_args.extend(["--pool-relay-port", str(pool_data.pool_relay_port)])

        if pool_data.multi_host_relay:
            relay_args.extend(["--multi-host-pool-relay", pool_data.multi_host_relay])

        metadata_args: list[str] = []
        if pool_data.pool_metadata_url and pool_data.pool_metadata_hash:
            metadata_args.extend(
                [
                    "--metadata-url",
                    str(pool_data.pool_metadata_url),
                    "--metadata-hash",
                    str(pool_data.pool_metadata_hash),
                ]
            )
            if pool_data.check_metadata_hash:
                metadata_args.append("--check-metadata-hash")

        reward_vkey_file = (
            reward_account_vkey_file
            if reward_account_vkey_file
            else next(iter(owner_stake_vkey_files))
        )

        reward_arg = [
            "--pool-reward-account-verification-key-file",
            str(reward_vkey_file),
        ]

        cmd = [
            *self._base,
            "registration-certificate",
            "--pool-pledge",
            str(pool_data.pool_pledge),
            "--pool-cost",
            str(pool_data.pool_cost),
            "--pool-margin",
            str(pool_data.pool_margin),
            "--vrf-verification-key-file",
            str(vrf_vkey_file),
            "--cold-verification-key-file",
            str(cold_vkey_file),
            *reward_arg,
            *helpers._prepend_flag(
                "--pool-owner-stake-verification-key-file",
                owner_stake_vkey_files,
            ),
            *metadata_args,
            *relay_args,
            *self._clusterlib_obj.magic_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)
        return out_file

    def gen_dereg_cert(
        self,
        *,
        name: str,
        cold_vkey_file: itp.FileType,
        epoch: int,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake pool deregistration certificate for compatible eras.

        Args:
            name: A name for the certificate file.
            cold_vkey_file: A path to cold verification key file.
            epoch: An epoch number for pool retirement.
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_pool_dereg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "deregistration-certificate",
            "--cold-verification-key-file",
            str(cold_vkey_file),
            "--epoch",
            str(epoch),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)
        return out_file


class GovernanceGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "governance")
        self.era = era

    def gen_mir_cert_to_treasury(
        self,
        *,
        name: str,
        transfer: int,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create MIR certificate transferring from reserves pot to treasury pot.

        Args:
            name: A name for the certificate file.
            transfer: An amount to transfer from reserves to treasury.
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{name}_mir_to_treasury.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "create-mir-certificate",
            "transfer-to-treasury",
            "--transfer",
            str(transfer),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)
        return out_file

    def gen_mir_cert_to_rewards(
        self,
        *,
        name: str,
        transfer: int,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create MIR certificate transferring from treasury pot to reserves pot.

        Args:
            name: A name for the certificate file.
            transfer: An amount to transfer from treasury to reserves.
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{name}_mir_to_rewards.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "create-mir-certificate",
            "transfer-to-rewards",
            "--transfer",
            str(transfer),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)
        return out_file

    def gen_pparams_update(
        self,
        *,
        name: str,
        epoch: int,
        genesis_vkey_file: itp.FileType,
        cli_args: itp.UnpackableSequence,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a protocol parameters update proposal for compatible eras.

        Args:
            name: A name for the proposal file.
            epoch: An epoch number when the update should take effect.
            genesis_vkey_file: A path to genesis verification key file.
            cli_args: Additional CLI arguments for protocol parameter updates.
            destination_dir: A path to directory for storing the proposal file (optional).

        Returns:
            pl.Path: A path to the generated proposal file.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_pparams_update.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "action",
            "create-protocol-parameters-update",
            "--epoch",
            str(epoch),
            "--genesis-verification-key-file",
            str(genesis_vkey_file),
            *cli_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def gen_mir_cert_stake_addr(
        self,
        *,
        name: str,
        stake_address: str,
        reward: int,
        use_treasury: bool = False,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create MIR certificate paying a stake address.

        Args:
            name: A name for the certificate file.
            stake_address: A stake address to receive the reward.
            reward: An amount of reward to pay.
            use_treasury: A bool indicating whether to use treasury as source (False uses reserves).
            destination_dir: A path to directory for storing the certificate file (optional).

        Returns:
            pl.Path: A path to the generated certificate file.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        funds_src = "treasury" if use_treasury else "reserves"
        out_file = destination_dir / f"{name}_{funds_src}_mir_stake.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "create-mir-certificate",
            "stake-addresses",
            f"--{funds_src}",
            "--stake-address",
            stake_address,
            "--reward",
            str(reward),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)
        return out_file


class TransactionGroup:
    """Compatible transaction commands for legacy eras (Alonzo / Mary / Babbage).

    This is a lightweight wrapper around:
    - txtools.collect_data_for_build (For Utxo selection balancing and deposits)
    - `cardano-cli compatible <era> transaction signed-transaction`

    It is intentionally simpler than the Conway TransactionGroup:
    - No Plutus scripts
    - No minting or burning
    - No withdrawals
    - No collateral
    - No reference inputs

    Main use for compatible eras:
    - simple ADA transfers
    - stake key registration or deregistration
    - pool registration or deregistration
    - governance certificates (MIR, genesis delegation, protocol parameter updates)
    """

    def __init__(self, clusterlib_obj: "itp.ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "transaction")
        self.era = era

    def gen_signed_tx_bare(
        self,
        *,
        name: str,
        txins: structs.OptionalUTXOData,
        txouts: list[structs.TxOut],
        tx_files: structs.TxFiles,
        fee: int,
        src_address: str = "",
        treasury_donation: int | None = None,
        script_valid: bool = True,
        destination_dir: itp.FileType = ".",
        join_txouts: bool = True,
    ) -> structs.TxRawOutput:
        """Generate a signed transaction using pre-balanced inputs and outputs.

        Assumes `txins` already contain selected UTxOs, `txouts` are already balanced
        (including change and deposits), and `fee` is already decided.

        Args:
            name: A name for the transaction file.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs.
            txouts: A list of `structs.TxOut`, specifying transaction outputs.
            tx_files: A `structs.TxFiles` container with transaction files.
            fee: A fee amount.
            src_address: A source address for change (optional).
            treasury_donation: A donation to the treasury to perform (optional).
            script_valid: A bool indicating that the script is valid (True by default).
            destination_dir: A path to directory for storing the transaction file (optional).
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).

        Returns:
            structs.TxRawOutput: A data container with transaction output details.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_tx.signed"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        txout_args, processed_txouts, txouts_count = txtools._process_txouts(
            txouts=list(txouts),
            join_txouts=join_txouts,
        )

        txin_strings = txtools._get_txin_strings(
            txins=txins,
            script_txins=(),  # No script support in compatible mode
        )

        build_args = [
            *self._base,
            "signed-transaction",
            *helpers._prepend_flag("--tx-in", txin_strings),
            *txout_args,
            *helpers._prepend_flag("--certificate-file", tx_files.certificate_files),
            *helpers._prepend_flag("--signing-key-file", tx_files.signing_key_files),
            *self._clusterlib_obj.magic_args,
            "--fee",
            str(fee),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(build_args, add_default_args=False)
        helpers._check_outfiles(out_file)

        return structs.TxRawOutput(
            txins=list(txins),
            txouts=processed_txouts,
            txouts_count=txouts_count,
            tx_files=tx_files,
            out_file=out_file,
            fee=fee,
            build_args=build_args,
            era=self._clusterlib_obj.era_in_use,
            script_txins=(),
            script_withdrawals=(),
            script_votes=(),
            complex_certs=(),
            complex_proposals=(),
            mint=(),
            invalid_hereafter=None,
            invalid_before=None,
            current_treasury_value=None,
            treasury_donation=treasury_donation,
            withdrawals=(),
            change_address=src_address,
            return_collateral_txouts=(),
            total_collateral_amount=None,
            readonly_reference_txins=(),
            script_valid=script_valid,
            required_signers=tx_files.signing_key_files,
            required_signer_hashes=(),
            combined_reference_txins=(),
        )

    def gen_signed_tx(
        self,
        *,
        name: str,
        src_address: str,
        txouts: structs.OptionalTxOuts,
        tx_files: structs.TxFiles,
        fee: int,
        txins: structs.OptionalUTXOData = (),
        deposit: int | None = None,
        treasury_donation: int | None = None,
        src_addr_utxos: list[structs.UTXOData] | None = None,
        destination_dir: itp.FileType = ".",
        join_txouts: bool = True,
        skip_asset_balancing: bool = False,
        script_valid: bool = True,
    ) -> structs.TxRawOutput:
        """Build and sign a compatible transaction.

        High-level helper that reuses `txtools.collect_data_for_build` to select UTxOs
        (if `txins` not provided), compute deposits (stake key, pool, governance), and
        balance outputs and change. Then calls `gen_signed_tx_bare` to run `signed-transaction`.

        Args:
            name: A name for the transaction file.
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs.
            tx_files: A `structs.TxFiles` container with transaction files.
            fee: A fee amount.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            deposit: A deposit amount needed by the transaction (optional).
            treasury_donation: A donation to the treasury to perform (optional).
            src_addr_utxos: A list of UTxOs for the source address (optional).
            destination_dir: A path to directory for storing the transaction file (optional).
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).
            skip_asset_balancing: A bool indicating if assets balancing should be skipped
                (`build` command balance the assets automatically in newer versions).
            script_valid: A bool indicating that the script is valid (True by default).

        Returns:
            structs.TxRawOutput: A data container with transaction output details.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        effective_tx_files = tx_files or structs.TxFiles()

        collected = txtools.collect_data_for_build(
            clusterlib_obj=self._clusterlib_obj,
            src_address=src_address,
            txins=txins,
            txouts=list(txouts),
            script_txins=(),
            mint=(),
            tx_files=effective_tx_files,
            complex_certs=(),
            complex_proposals=(),
            fee=fee,
            withdrawals=(),
            script_withdrawals=(),
            deposit=deposit,
            treasury_donation=treasury_donation or 0,
            src_addr_utxos=src_addr_utxos,
            skip_asset_balancing=skip_asset_balancing,
        )

        return self.gen_signed_tx_bare(
            name=name,
            txins=collected.txins,
            txouts=collected.txouts,
            tx_files=effective_tx_files,
            fee=fee,
            src_address=src_address,
            treasury_donation=treasury_donation,
            script_valid=script_valid,
            destination_dir=destination_dir_path,
            join_txouts=join_txouts,
        )

    def __repr__(self) -> str:
        return f"<TransactionGroup era={self.era} base={self._base}>"
