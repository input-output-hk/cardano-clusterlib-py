"""Wrapper for cardano-cli for working with cardano cluster."""
import contextlib
import datetime
import functools
import json
import logging
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import txtools
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType
from cardano_clusterlib.types import UnpackableSequence


LOGGER = logging.getLogger(__name__)


class QueryGroup:
    # pylint: disable=too-many-public-methods

    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def query_cli(self, cli_args: UnpackableSequence) -> str:
        """Run the `cardano-cli query` command."""
        stdout = self._clusterlib_obj.cli(
            [
                "query",
                *cli_args,
                *self._clusterlib_obj.magic_args,
                f"--{self._clusterlib_obj.protocol}-mode",
            ]
        ).stdout
        stdout_dec = stdout.decode("utf-8") if stdout else ""
        return stdout_dec

    def get_utxo(
        self,
        address: Union[str, List[str]] = "",
        txin: Union[str, List[str]] = "",
        utxo: Union[structs.UTXOData, structs.OptionalUTXOData] = (),
        tx_raw_output: Optional[structs.TxRawOutput] = None,
        coins: UnpackableSequence = (),
    ) -> List[structs.UTXOData]:
        """Return UTxO info for payment address.

        Args:
            address: Payment address(es).
            txin: Transaction input(s) (TxId#TxIx).
            utxo: Representation of UTxO data (`structs.UTXOData`).
            tx_raw_output: A data used when building a transaction (`structs.TxRawOutput`).
            coins: A list (iterable) of coin names (asset IDs, optional).

        Returns:
            List[structs.UTXOData]: A list of UTxO data.
        """
        cli_args = ["utxo", "--out-file", "/dev/stdout"]

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
            raise AssertionError(
                "Either `address`, `txin`, `utxo` or `tx_raw_output` need to be specified."
            )

        utxo_dict = json.loads(self.query_cli(cli_args))
        utxos = txtools.get_utxo(utxo_dict=utxo_dict, address=address_single, coins=coins)
        if sort_results:
            utxos = sorted(utxos, key=lambda u: u.utxo_ix)
        return utxos

    def get_tip(self) -> Dict[str, Any]:
        """Return current tip - last block successfully applied to the ledger."""
        tip: Dict[str, Any] = json.loads(self.query_cli(["tip"]))

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
        destination_dir: FileType = ".",
    ) -> Path:
        """Save ledger state to file.

        Args:
            state_name: A name of the ledger state (can be epoch number, etc.).
            destination_dir: A path to directory for storing the state JSON file (optional).

        Returns:
            Path: A path to the generated state JSON file.
        """
        json_file = Path(destination_dir) / f"{state_name}_ledger_state.json"
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
        self, stake_pool_ids: Optional[List[str]] = None, all_stake_pools: bool = False
    ) -> Dict[str, Any]:
        """Return the three stake snapshots, plus the total active stake.

        Args:
            stake_pool_ids: A list of stake pool IDs, Bech32-encoded or hex-encoded (optional).
            all_stake_pools: A bool indicating whether to query for all stake pools (optional).

        Returns:
            Dict: A stake snapshot data.
        """
        query_args = ["stake-snapshot"]

        if all_stake_pools:
            query_args.extend(["--all-stake-pools"])
        elif stake_pool_ids:
            query_args.extend(helpers._prepend_flag("--stake-pool-id", stake_pool_ids))

        stake_snapshot: Dict[str, Any] = json.loads(self.query_cli(query_args))
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
        pool_params: dict = json.loads(
            self.query_cli(["pool-params", "--stake-pool-id", stake_pool_id])
        )

        # in node 1.35.1+ the information is nested under hex encoded stake pool ID
        if pool_params and "poolParams" not in pool_params:
            pool_params = next(iter(pool_params.values()))

        retiring = pool_params.get("retiring")  # pool retiring epoch
        pparams_top = structs.PoolParamsTop(
            pool_params=pool_params.get("poolParams") or {},
            future_pool_params=pool_params.get("futurePoolParams") or {},
            retiring=int(retiring) if retiring is not None else None,
        )
        return pparams_top

    def get_stake_addr_info(self, stake_addr: str) -> structs.StakeAddrInfo:
        """Return the current delegations and reward accounts filtered by stake address.

        Args:
            stake_addr: A stake address string.

        Returns:
            structs.StakeAddrInfo: A tuple containing stake address info.
        """
        output_json = json.loads(self.query_cli(["stake-address-info", "--address", stake_addr]))
        if not output_json:
            return structs.StakeAddrInfo(address="", delegation="", reward_account_balance=0)

        address_rec = list(output_json)[0]
        address = address_rec.get("address") or ""
        delegation = address_rec.get("delegation") or ""
        reward_account_balance = address_rec.get("rewardAccountBalance") or 0
        return structs.StakeAddrInfo(
            address=address,
            delegation=delegation,
            reward_account_balance=reward_account_balance,
        )

    def get_address_deposit(self) -> int:
        """Return stake address deposit amount."""
        pparams = self.get_protocol_params()
        return pparams.get("stakeAddressDeposit") or 0

    def get_pool_deposit(self) -> int:
        """Return stake pool deposit amount."""
        pparams = self.get_protocol_params()
        return pparams.get("stakePoolDeposit") or 0

    def get_stake_distribution(self) -> Dict[str, float]:
        """Return current aggregated stake distribution per stake pool."""
        # stake pool values are displayed starting with line 2 of the command output
        result = self.query_cli(["stake-distribution"]).splitlines()[2:]
        stake_distribution: Dict[str, float] = {}
        for pool in result:
            pool_id, stake = pool.split()
            stake_distribution[pool_id] = float(stake)
        return stake_distribution

    def get_stake_pools(self) -> List[str]:
        """Return the node's current set of stake pool ids."""
        stake_pools = self.query_cli(["stake-pools"]).splitlines()
        return stake_pools

    def get_leadership_schedule(
        self,
        vrf_skey_file: FileType,
        stake_pool_vkey: str = "",
        cold_vkey_file: Optional[FileType] = None,
        stake_pool_id: str = "",
        for_next: bool = False,
    ) -> List[structs.LeadershipSchedule]:
        """Get the slots the node is expected to mint a block in.

        Args:
            vrf_vkey_file: A path to node VRF vkey file.
            stake_pool_vkey: A pool cold vkey (Bech32 or hex-encoded, optional)
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (Bech32 or hex-encoded, optional).
            for_next: A bool indicating whether to get the leadership schedule for the following
                epoch (current epoch by default)

        Returns:
            List[structs.LeadershipSchedule]: A list of `structs.LeadershipSchedule`, specifying
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
            raise AssertionError(
                "Either `stake_pool_vkey`, `cold_vkey_file` or `stake_pool_id` is needed."
            )

        args.append("--next" if for_next else "--current")

        unparsed = self.query_cli(
            [
                "leadership-schedule",
                "--genesis",
                str(self._clusterlib_obj.genesis_json),
                "--vrf-signing-key-file",
                str(vrf_skey_file),
                *args,
            ]
            # schedule values are displayed starting with line 2 of the command output
        ).splitlines()[2:]

        schedule = []
        for rec in unparsed:
            slot_no, date_str, time_str, *__ = rec.split()
            # add milliseconds component of a time string if it is missing
            time_str = time_str if "." in time_str else f"{time_str}.0"
            schedule.append(
                structs.LeadershipSchedule(
                    slot_no=int(slot_no),
                    utc_time=datetime.datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                    ),
                )
            )

        return schedule

    def get_slot_no(self) -> int:
        """Return slot number of last block that was successfully applied to the ledger."""
        return int(self.get_tip()["slot"])

    def get_block_no(self) -> int:
        """Return block number of last block that was successfully applied to the ledger."""
        return int(self.get_tip()["block"])

    def get_epoch(self) -> int:
        """Return epoch of last block that was successfully applied to the ledger."""
        return int(self.get_tip()["epoch"])

    def get_era(self) -> str:
        """Return network era."""
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
            structs.UTXOData: An UTxO record with the highest amount.
        """
        utxo = self.get_utxo(address=address, coins=[coin])
        highest_amount_rec = max(utxo, key=lambda x: x.amount)
        return highest_amount_rec

    def get_kes_period(self) -> int:
        """Return last block KES period."""
        return int(self.get_slot_no() // self._clusterlib_obj.slots_per_kes_period)

    def get_kes_period_info(self, opcert_file: FileType) -> Dict[str, Any]:
        """Get information about the current KES period and node's operational certificate.

        Args:
            opcert_file: A path to operational certificate.

        Returns:
            dict: A dictionary containing KES period information.
        """
        command_output = self.query_cli(["kes-period-info", "--op-cert-file", str(opcert_file)])
        return clusterlib_helpers._get_kes_period_info(kes_info=command_output)

    def get_mempool_info(self) -> Dict[str, Any]:
        """Return info about the current mempool's capacity and sizes.

        Returns:
            dict: A dictionary containing mempool information.
        """
        tx_mempool: Dict[str, Any] = json.loads(self.query_cli(["tx-mempool", "info"]))
        return tx_mempool

    def get_mempool_next_tx(self) -> Dict[str, Any]:
        """Return info about the next transaction in the mempool's current list.

        Returns:
            dict: A dictionary containing mempool information.
        """
        tx_mempool: Dict[str, Any] = json.loads(self.query_cli(["tx-mempool", "next-tx"]))
        return tx_mempool

    def get_mempool_tx_exists(self, txid: str) -> Dict[str, Any]:
        """Query if a particular transaction exists in the mempool.

        Args:
            txid: A transaction ID.

        Returns:
            dict: A dictionary containing mempool information.
        """
        tx_mempool: Dict[str, Any] = json.loads(self.query_cli(["tx-mempool", "tx-exists", txid]))
        return tx_mempool

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
