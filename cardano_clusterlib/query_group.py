"""Wrapper for cardano-cli for working with cardano cluster."""

import contextlib
import datetime
import functools
import json
import logging
import pathlib as pl
import typing as tp
import warnings

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import txtools
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class QueryGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def _get_cred_args(
        self,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: itp.FileType | None = None,
        drep_key_hash: str = "",
    ) -> list[str]:
        """Get arguments for script or verification key."""
        if drep_script_hash:
            cred_args = ["--drep-script-hash", str(drep_script_hash)]
        elif drep_vkey:
            cred_args = ["--drep-verification-key", str(drep_vkey)]
        elif drep_vkey_file:
            cred_args = ["--drep-verification-key-file", str(drep_vkey_file)]
        elif drep_key_hash:
            cred_args = ["--drep-key-hash", str(drep_key_hash)]
        else:
            cred_args = []

        return cred_args

    def query_cli(
        self, cli_args: itp.UnpackableSequence, cli_sub_args: itp.UnpackableSequence = ()
    ) -> str:
        """Run the `cardano-cli query` command."""
        stdout = self._clusterlib_obj.cli(
            [
                "query",
                *cli_args,
                *self._clusterlib_obj.magic_args,
                *self._clusterlib_obj.socket_args,
                *cli_sub_args,
            ]
        ).stdout
        stdout_dec = stdout.decode("utf-8") if stdout else ""
        return stdout_dec

    def get_utxo(
        self,
        address: str | list[str] = "",
        txin: str | list[str] = "",
        utxo: structs.UTXOData | structs.OptionalUTXOData = (),
        tx_raw_output: structs.TxRawOutput | None = None,
        coins: itp.UnpackableSequence = (),
    ) -> list[structs.UTXOData]:
        """Return UTxO info for payment address.

        Args:
            address: Payment address(es).
            txin: Transaction input(s) (TxId#TxIx).
            utxo: Representation of UTxO data (`structs.UTXOData`).
            tx_raw_output: A data used when building a transaction (`structs.TxRawOutput`).
            coins: A list (iterable) of coin names (asset IDs, optional).

        Returns:
            list[structs.UTXOData]: A list of UTxO data.
        """
        cli_args = ["utxo", "--output-json"]

        address_single = ""
        sort_results = False
        if address:
            if isinstance(address, str):
                address_single = address
                address = [address]
            cli_args.extend(helpers._prepend_flag("--address", address))
        elif txin:
            if isinstance(txin, str):
                txin = [txin]
            cli_args.extend(helpers._prepend_flag("--tx-in", txin))
        elif utxo:
            if isinstance(utxo, structs.UTXOData):
                utxo = [utxo]
            utxo_formatted = [f"{u.utxo_hash}#{u.utxo_ix}" for u in utxo]
            cli_args.extend(helpers._prepend_flag("--tx-in", utxo_formatted))
        elif tx_raw_output:
            sort_results = True
            change_txout_num = 1 if tx_raw_output.change_address else 0
            return_collateral_txout_num = 1 if tx_raw_output.script_txins else 0
            num_of_txouts = (
                tx_raw_output.txouts_count + change_txout_num + return_collateral_txout_num
            )
            utxo_hash = self._clusterlib_obj.g_transaction.get_txid(
                tx_body_file=tx_raw_output.out_file
            )
            utxo_formatted = [f"{utxo_hash}#{ix}" for ix in range(num_of_txouts)]
            cli_args.extend(helpers._prepend_flag("--tx-in", utxo_formatted))
        else:
            msg = "Either `address`, `txin`, `utxo` or `tx_raw_output` need to be specified."
            raise AssertionError(msg)

        utxo_dict = json.loads(self.query_cli(cli_args))
        utxos = txtools.get_utxo(utxo_dict=utxo_dict, address=address_single, coins=coins)
        if sort_results:
            utxos = sorted(utxos, key=lambda u: u.utxo_ix)
        return utxos

    def get_tip(self) -> dict[str, tp.Any]:
        """Return current tip - last block successfully applied to the ledger."""
        tip: dict[str, tp.Any] = json.loads(self.query_cli(["tip"]))

        # "syncProgress" is returned as string
        sync_progress = tip.get("syncProgress")
        if sync_progress:
            with contextlib.suppress(ValueError):
                tip["syncProgress"] = float(sync_progress)

        return tip

    def get_ledger_state(self) -> dict:
        """Return the current ledger state info."""
        ledger_state: dict = json.loads(self.query_cli(["ledger-state"]))
        return ledger_state

    def save_ledger_state(
        self,
        state_name: str,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Save ledger state to file.

        Args:
            state_name: A name of the ledger state (can be epoch number, etc.).
            destination_dir: A path to directory for storing the state JSON file (optional).

        Returns:
            Path: A path to the generated state JSON file.
        """
        json_file = pl.Path(destination_dir) / f"{state_name}_ledger_state.json"
        # TODO: workaround for https://github.com/input-output-hk/cardano-node/issues/2461
        # self.query_cli(["ledger-state", "--out-file", str(json_file)])
        ledger_state = self.get_ledger_state()
        with open(json_file, "w", encoding="utf-8") as fp_out:
            json.dump(ledger_state, fp_out, indent=4)
        return json_file

    def get_protocol_state(self) -> dict:
        """Return the current protocol state info."""
        protocol_state: dict = json.loads(self.query_cli(["protocol-state"]))
        return protocol_state

    def get_protocol_params(self) -> dict:
        """Return the current protocol parameters."""
        self._clusterlib_obj.refresh_pparams_file()
        with open(self._clusterlib_obj.pparams_file, encoding="utf-8") as in_json:
            pparams: dict = json.load(in_json)
        return pparams

    def get_registered_stake_pools_ledger_state(self) -> dict:
        """Return ledger state info for registered stake pools."""
        registered_pools_details: dict = self.get_ledger_state()["stateBefore"]["esLState"][
            "delegationState"
        ]["pstate"]["pParams pState"]
        return registered_pools_details

    def get_stake_snapshot(
        self, stake_pool_ids: tp.Optional[list[str]] = None, all_stake_pools: bool = False
    ) -> dict[str, tp.Any]:
        """Return the three stake snapshots, plus the total active stake.

        Args:
            stake_pool_ids: A list of stake pool IDs, Bech32-encoded or hex-encoded (optional).
            all_stake_pools: A bool indicating whether to query for all stake pools (optional).

        Returns:
            dict: A stake snapshot data.
        """
        query_args = ["stake-snapshot"]

        if all_stake_pools:
            query_args.extend(["--all-stake-pools"])
        elif stake_pool_ids:
            query_args.extend(helpers._prepend_flag("--stake-pool-id", stake_pool_ids))

        stake_snapshot: dict[str, tp.Any] = json.loads(self.query_cli(query_args))
        return stake_snapshot

    def get_pool_params(
        self,
        stake_pool_id: str,
    ) -> structs.PoolParamsTop:
        """Return a pool parameters.

        Args:
            stake_pool_id: An ID of the stake pool (Bech32-encoded or hex-encoded).

        Returns:
            dict: A pool parameters.
        """
        warnings.warn(
            "`pool-params` deprecated by `pool-state` for node 1.35.4+",
            DeprecationWarning,
            stacklevel=2,
        )

        pool_params: dict = json.loads(
            self.query_cli(["pool-params", "--stake-pool-id", stake_pool_id])
        )

        # In node 1.35.1+ the information is nested under hex encoded stake pool ID
        if pool_params and "poolParams" not in pool_params:
            pool_params = next(iter(pool_params.values()))

        retiring = pool_params.get("retiring")  # pool retiring epoch
        pparams_top = structs.PoolParamsTop(
            pool_params=pool_params.get("poolParams") or {},
            future_pool_params=pool_params.get("futurePoolParams") or {},
            retiring=int(retiring) if retiring is not None else None,
        )
        return pparams_top

    def get_pool_state(
        self,
        stake_pool_id: str,
    ) -> structs.PoolParamsTop:
        """Return a pool state.

        Args:
            stake_pool_id: An ID of the stake pool (Bech32-encoded or hex-encoded).

        Returns:
            dict: A pool parameters.
        """
        pool_state: dict = json.loads(
            self.query_cli(["pool-state", "--stake-pool-id", stake_pool_id])
        )

        # The information is nested under hex encoded stake pool ID
        if pool_state:
            pool_state = next(iter(pool_state.values()))

        retiring = pool_state.get("retiring")  # pool retiring epoch
        pparams_top = structs.PoolParamsTop(
            pool_params=pool_state.get("poolParams") or {},
            future_pool_params=pool_state.get("futurePoolParams") or {},
            retiring=int(retiring) if retiring is not None else None,
        )
        return pparams_top

    def get_stake_addr_info(self, stake_addr: str) -> structs.StakeAddrInfo:
        """Return the current delegations and reward accounts filtered by stake address.

        Args:
            stake_addr: A stake address string.

        Returns:
            structs.StakeAddrInfo: A data container containing stake address info.
        """
        output_json = json.loads(self.query_cli(["stake-address-info", "--address", stake_addr]))
        if not output_json:
            return structs.StakeAddrInfo(
                address="",
                delegation="",
                reward_account_balance=0,
                registration_deposit=-1,
                vote_delegation="",
            )

        address_rec = next(iter(output_json))
        address = address_rec.get("address") or ""
        delegation = address_rec.get("delegation") or address_rec.get("stakeDelegation") or ""
        reward_account_balance = address_rec.get("rewardAccountBalance") or 0
        tmp_deposit = address_rec.get("stakeRegistrationDeposit") or address_rec.get(
            "delegationDeposit"
        )
        registration_deposit = -1 if tmp_deposit is None else tmp_deposit
        vote_delegation = address_rec.get("voteDelegation") or ""
        return structs.StakeAddrInfo(
            address=address,
            delegation=delegation,
            reward_account_balance=reward_account_balance,
            registration_deposit=registration_deposit,
            vote_delegation=vote_delegation,
        )

    def get_address_deposit(self, pparams: dict[str, tp.Any] | None = None) -> int:
        """Return stake address deposit amount."""
        pparams = pparams or self.get_protocol_params()
        return pparams.get("stakeAddressDeposit") or 0

    def get_pool_deposit(self, pparams: dict[str, tp.Any] | None = None) -> int:
        """Return stake pool deposit amount."""
        pparams = pparams or self.get_protocol_params()
        return pparams.get("stakePoolDeposit") or 0

    def get_drep_deposit(self, pparams: dict[str, tp.Any] | None = None) -> int:
        """Return DRep deposit amount."""
        pparams = pparams or self.get_protocol_params()
        return pparams.get("dRepDeposit") or 0

    def get_gov_action_deposit(self, pparams: dict[str, tp.Any] | None = None) -> int:
        """Return governance action deposit amount."""
        pparams = pparams or self.get_protocol_params()
        return pparams.get("govActionDeposit") or 0

    def get_stake_distribution(self) -> dict[str, float]:
        """Return current aggregated stake distribution per stake pool."""
        # Stake pool values are displayed starting with line 2 of the command output
        result = self.query_cli(["stake-distribution", "--output-text"]).splitlines()[2:]
        stake_distribution: dict[str, float] = {}
        for pool in result:
            pool_id, stake = pool.split()
            stake_distribution[pool_id] = float(stake)
        return stake_distribution

    def get_stake_pools(self) -> list[str]:
        """Return the node's current set of stake pool ids."""
        stake_pools = self.query_cli(["stake-pools", "--output-text"]).splitlines()
        return stake_pools

    def get_leadership_schedule(
        self,
        vrf_skey_file: itp.FileType,
        stake_pool_vkey: str = "",
        cold_vkey_file: itp.FileType | None = None,
        stake_pool_id: str = "",
        for_next: bool = False,
    ) -> list[structs.LeadershipSchedule]:
        """Get the slots the node is expected to mint a block in.

        Args:
            vrf_skey_file: A path to node VRF skey file.
            stake_pool_vkey: A pool cold vkey (Bech32 or hex-encoded, optional)
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (Bech32 or hex-encoded, optional).
            for_next: A bool indicating whether to get the leadership schedule for the following
                epoch (current epoch by default)

        Returns:
            list[structs.LeadershipSchedule]: A list of `structs.LeadershipSchedule`, specifying
                slot and time.
        """
        args = []

        if stake_pool_vkey:
            args.extend(
                [
                    "--stake-pool-verification-key",
                    str(stake_pool_vkey),
                ]
            )
        elif cold_vkey_file:
            args.extend(
                [
                    "--cold-verification-key-file",
                    str(cold_vkey_file),
                ]
            )
        elif stake_pool_id:
            args.extend(
                [
                    "--stake-pool-id",
                    str(stake_pool_id),
                ]
            )
        else:
            msg = "Either `stake_pool_vkey`, `cold_vkey_file` or `stake_pool_id` is needed."
            raise AssertionError(msg)

        args.append("--next" if for_next else "--current")

        unparsed = self.query_cli(
            [
                "leadership-schedule",
                "--output-text",
                "--genesis",
                str(self._clusterlib_obj.genesis_json),
                "--vrf-signing-key-file",
                str(vrf_skey_file),
                *args,
            ]
            # Schedule values are displayed starting with line 2 of the command output
        ).splitlines()[2:]

        schedule = []
        for rec in unparsed:
            slot_no, date_str, time_str, *__ = rec.split()
            # Add milliseconds component of a time string if it is missing
            time_str = time_str if "." in time_str else f"{time_str}.0"
            schedule.append(
                structs.LeadershipSchedule(
                    slot_no=int(slot_no),
                    utc_time=datetime.datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                    ).replace(tzinfo=datetime.timezone.utc),
                )
            )

        return schedule

    def get_slot_no(self, tip: dict[str, tp.Any] | None = None) -> int:
        """Return slot number of last block that was successfully applied to the ledger."""
        tip = tip or self.get_tip()
        return int(self.get_tip()["slot"])

    def get_block_no(self, tip: dict[str, tp.Any] | None = None) -> int:
        """Return block number of last block that was successfully applied to the ledger."""
        tip = tip or self.get_tip()
        return int(self.get_tip()["block"])

    def get_epoch(self, tip: dict[str, tp.Any] | None = None) -> int:
        """Return epoch of last block that was successfully applied to the ledger."""
        tip = tip or self.get_tip()
        return int(self.get_tip()["epoch"])

    def get_epoch_slot_no(self, tip: dict[str, tp.Any] | None = None) -> int:
        """Return slot number within a given epoch.

        (of last block successfully applied to the ledger)
        """
        tip = tip or self.get_tip()
        return int(self.get_tip()["slotInEpoch"])

    def get_slots_to_epoch_end(self, tip: dict[str, tp.Any] | None = None) -> int:
        """Return the number of slots left until the epoch end."""
        tip = tip or self.get_tip()
        return int(self.get_tip()["slotsToEpochEnd"])

    def get_era(self, tip: dict[str, tp.Any] | None = None) -> str:
        """Return network era."""
        tip = tip or self.get_tip()
        era: str = self.get_tip()["era"]
        return era

    def get_address_balance(self, address: str, coin: str = consts.DEFAULT_COIN) -> int:
        """Get total balance of an address (sum of all UTxO balances).

        Args:
            address: A payment address string.
            coin: A coin name (asset IDs).

        Returns:
            int: A total balance.
        """
        utxo = self.get_utxo(address=address, coins=[coin])
        address_balance = functools.reduce(lambda x, y: x + y.amount, utxo, 0)
        return int(address_balance)

    def get_utxo_with_highest_amount(
        self, address: str, coin: str = consts.DEFAULT_COIN
    ) -> structs.UTXOData:
        """Return data for UTxO with the highest amount.

        Args:
            address: A payment address string.
            coin: A coin name (asset IDs).

        Returns:
            structs.UTXOData: A UTxO record with the highest amount.
        """
        utxo = self.get_utxo(address=address, coins=[coin])
        highest_amount_rec = max(utxo, key=lambda x: x.amount)
        return highest_amount_rec

    def get_kes_period(self) -> int:
        """Return last block KES period."""
        return int(self.get_slot_no() // self._clusterlib_obj.slots_per_kes_period)

    def get_kes_period_info(self, opcert_file: itp.FileType) -> dict[str, tp.Any]:
        """Get information about the current KES period and node's operational certificate.

        Args:
            opcert_file: A path to operational certificate.

        Returns:
            dict: A dictionary containing KES period information.
        """
        command_output = self.query_cli(["kes-period-info", "--op-cert-file", str(opcert_file)])
        return clusterlib_helpers._get_kes_period_info(kes_info=command_output)

    def get_mempool_info(self) -> dict[str, tp.Any]:
        """Return info about the current mempool's capacity and sizes.

        Returns:
            dict: A dictionary containing mempool information.
        """
        tx_mempool: dict[str, tp.Any] = json.loads(
            self.query_cli(["tx-mempool"], cli_sub_args=[consts.SUBCOMMAND_MARK, "info"])
        )
        return tx_mempool

    def get_mempool_next_tx(self) -> dict[str, tp.Any]:
        """Return info about the next transaction in the mempool's current list.

        Returns:
            dict: A dictionary containing mempool information.
        """
        tx_mempool: dict[str, tp.Any] = json.loads(
            self.query_cli(["tx-mempool"], cli_sub_args=[consts.SUBCOMMAND_MARK, "next-tx"])
        )
        return tx_mempool

    def get_mempool_tx_exists(self, txid: str) -> dict[str, tp.Any]:
        """Query if a particular transaction exists in the mempool.

        Args:
            txid: A transaction ID.

        Returns:
            dict: A dictionary containing mempool information.
        """
        tx_mempool: dict[str, tp.Any] = json.loads(
            self.query_cli(["tx-mempool"], cli_sub_args=[consts.SUBCOMMAND_MARK, "tx-exists", txid])
        )
        return tx_mempool

    def get_slot_number(self, timestamp: datetime.datetime) -> int:
        """Return slot number for UTC timestamp."""
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

        slot_number: int = json.loads(self.query_cli(["slot-number", timestamp_str]))

        return slot_number

    def get_constitution(self) -> dict[str, tp.Any]:
        """Get the constitution."""
        out: dict[str, tp.Any] = json.loads(self.query_cli(["constitution"]))
        return out

    def get_gov_state(self) -> dict[str, tp.Any]:
        """Get the governance state."""
        out: dict[str, tp.Any] = json.loads(self.query_cli(["gov-state"]))
        return out

    def get_drep_state(
        self,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: itp.FileType | None = None,
        drep_key_hash: str = "",
    ) -> list[list[dict[str, tp.Any]]]:
        """Get the DRep state.

        When no key is provided, query all DReps.

        Args:
            drep_script_hash: DRep script hash (hex-encoded, optional).
            drep_vkey: DRep verification key (Bech32 or hex-encoded).
            drep_vkey_file: Filepath of the DRep verification key.
            drep_key_hash: DRep verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            list[list[dict[str, Any]]]: DRep state.
        """
        cred_args = self._get_cred_args(
            drep_script_hash=drep_script_hash,
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
        )
        if not cred_args:
            cred_args = ["--all-dreps"]

        out: list[list[dict[str, tp.Any]]] = json.loads(self.query_cli(["drep-state", *cred_args]))
        return out

    def get_drep_stake_distribution(
        self,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: itp.FileType | None = None,
        drep_key_hash: str = "",
    ) -> dict[str, tp.Any]:
        """Get the DRep stake distribution.

        When no key is provided, query all DReps.

        Args:
            drep_script_hash: DRep script hash (hex-encoded, optional).
            drep_vkey: DRep verification key (Bech32 or hex-encoded).
            drep_vkey_file: Filepath of the DRep verification key.
            drep_key_hash: DRep verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            dict[str, Any]: DRep stake distribution.
        """
        cred_args = self._get_cred_args(
            drep_script_hash=drep_script_hash,
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
        )
        if not cred_args:
            cred_args = ["--all-dreps"]

        out: list[list] | dict[str, tp.Any] = json.loads(
            self.query_cli(["drep-stake-distribution", *cred_args])
        )
        recs: dict[str, tp.Any] = {i[0]: i[1] for i in out} if isinstance(out, list) else out
        return recs

    def get_spo_stake_distribution(
        self,
        spo_vkey: str = "",
        spo_vkey_file: itp.FileType | None = None,
        spo_key_hash: str = "",
    ) -> list[structs.SPOStakeDistrib]:
        """Get the SPO stake distribution.

        When no key is provided, query all SPOs.

        Args:
            spo_vkey: SPO verification key (Bech32 or hex-encoded).
            spo_vkey_file: Filepath of the SPO verification key.
            spo_key_hash: SPO verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            list[structs.SPOStakeDistrib]: SPO stake distribution.
        """
        if spo_vkey:
            cred_args = ["--spo-verification-key", str(spo_vkey)]
        elif spo_vkey_file:
            cred_args = ["--spo-verification-key-file", str(spo_vkey_file)]
        elif spo_key_hash:
            cred_args = ["--spo-key-hash", str(spo_key_hash)]
        else:
            cred_args = []
        if not cred_args:
            cred_args = ["--all-spos"]

        out: list[list] = json.loads(self.query_cli(["spo-stake-distribution", *cred_args]))
        recs = [
            structs.SPOStakeDistrib(
                spo_vkey_hex=r[0], stake_distribution=r[1], vote_delegation=r[2] or ""
            )
            for r in out
        ]
        return recs

    def get_committee_state(self) -> dict[str, tp.Any]:
        """Get the committee state."""
        out: dict[str, tp.Any] = json.loads(self.query_cli(["committee-state"]))
        return out

    def get_treasury(self) -> int:
        """Get the treasury value."""
        return int(self.query_cli(["treasury"]))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
