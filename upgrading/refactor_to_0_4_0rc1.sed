# use as `sed -i -f refactor_to_0_4_0rc1.sed *.py`
# match 'cluster.*' and not 'clusterlib_utils.*'
s/cluste\(r[^l][^(.]*\|r\)\.gen_payment_addr_and_keys(/cluste\1.g_address.gen_payment_addr_and_keys(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_payment_addr(/cluste\1.g_address.gen_payment_addr(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_payment_key_pair(/cluste\1.g_address.gen_payment_key_pair(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_payment_vkey_hash(/cluste\1.g_address.get_payment_vkey_hash(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_address_info(/cluste\1.g_address.get_address_info(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_script_addr(/cluste\1.g_address.gen_script_addr(/g

s/cluste\(r[^l][^(.]*\|r\)\.genesis_keys/cluste\1.g_genesis.genesis_keys/g
s/cluste\(r[^l][^(.]*\|r\)\.genesis_utxo_addr/cluste\1.g_genesis.genesis_utxo_addr/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_genesis_addr(/cluste\1.g_genesis.gen_genesis_addr(/g

s/cluste\(r[^l][^(.]*\|r\)\.gen_update_proposal(/cluste\1.g_governance.gen_update_proposal(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_mir_cert_to_treasury(/cluste\1.g_governance.gen_mir_cert_to_treasury(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_mir_cert_to_rewards(/cluste\1.g_governance.gen_mir_cert_to_rewards(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_mir_cert_stake_addr(/cluste\1.g_governance.gen_mir_cert_stake_addr(/g
s/cluste\(r[^l][^(.]*\|r\)\.submit_update_proposal(/cluste\1.g_governance.submit_update_proposal(/g

s/cluste\(r[^l][^(.]*\|r\)\.gen_verification_key(/cluste\1.g_key.gen_verification_key(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_non_extended_verification_key(/cluste\1.g_key.gen_non_extended_verification_key(/g

s/cluste\(r[^l][^(.]*\|r\)\.gen_kes_key_pair(/cluste\1.g_node.gen_kes_key_pair(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_vrf_key_pair(/cluste\1.g_node.gen_vrf_key_pair(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_cold_key_pair_and_counter(/cluste\1.g_node.gen_cold_key_pair_and_counter(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_node_operational_cert(/cluste\1.g_node.gen_node_operational_cert(/g

s/cluste\(r[^l][^(.]*\|r\)\.query_cli(/cluste\1.g_query.query_cli(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_utxo(/cluste\1.g_query.get_utxo(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_tip(/cluste\1.g_query.get_tip(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_ledger_state(/cluste\1.g_query.get_ledger_state(/g
s/cluste\(r[^l][^(.]*\|r\)\.save_ledger_state(/cluste\1.g_query.save_ledger_state(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_protocol_state(/cluste\1.g_query.get_protocol_state(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_protocol_params(/cluste\1.g_query.get_protocol_params(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_registered_stake_pools_ledger_state(/cluste\1.g_query.get_registered_stake_pools_ledger_state(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_stake_snapshot(/cluste\1.g_query.get_stake_snapshot(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_pool_params(/cluste\1.g_query.get_pool_params(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_stake_addr_info(/cluste\1.g_query.get_stake_addr_info(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_address_deposit(/cluste\1.g_query.get_address_deposit(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_pool_deposit(/cluste\1.g_query.get_pool_deposit(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_stake_distribution(/cluste\1.g_query.get_stake_distribution(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_stake_pools(/cluste\1.g_query.get_stake_pools(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_leadership_schedule(/cluste\1.g_query.get_leadership_schedule(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_slot_no(/cluste\1.g_query.get_slot_no(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_block_no(/cluste\1.g_query.get_block_no(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_epoch(/cluste\1.g_query.get_epoch(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_era(/cluste\1.g_query.get_era(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_address_balance(/cluste\1.g_query.get_address_balance(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_utxo_with_highest_amount(/cluste\1.g_query.get_utxo_with_highest_amount(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_kes_period(/cluste\1.g_query.get_kes_period(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_kes_period_info(/cluste\1.g_query.get_kes_period_info(/g

s/cluste\(r[^l][^(.]*\|r\)\.gen_stake_addr(/cluste\1.g_stake_address.gen_stake_addr(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_stake_key_pair(/cluste\1.g_stake_address.gen_stake_key_pair(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_stake_addr_registration_cert(/cluste\1.g_stake_address.gen_stake_addr_registration_cert(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_stake_addr_deregistration_cert(/cluste\1.g_stake_address.gen_stake_addr_deregistration_cert(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_stake_addr_delegation_cert(/cluste\1.g_stake_address.gen_stake_addr_delegation_cert(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_stake_addr_and_keys(/cluste\1.g_stake_address.gen_stake_addr_and_keys(/g
s/cluste\(r[^l][^(.]*\|r\)\.withdraw_reward(/cluste\1.g_stake_address.withdraw_reward(/g

s/cluste\(r[^l][^(.]*\|r\)\.gen_pool_metadata_hash(/cluste\1.g_stake_pool.gen_pool_metadata_hash(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_pool_registration_cert(/cluste\1.g_stake_pool.gen_pool_registration_cert(/g
s/cluste\(r[^l][^(.]*\|r\)\.gen_pool_deregistration_cert(/cluste\1.g_stake_pool.gen_pool_deregistration_cert(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_stake_pool_id(/cluste\1.g_stake_pool.get_stake_pool_id(/g
s/cluste\(r[^l][^(.]*\|r\)\.create_stake_pool(/cluste\1.g_stake_pool.create_stake_pool(/g
s/cluste\(r[^l][^(.]*\|r\)\.register_stake_pool(/cluste\1.g_stake_pool.register_stake_pool(/g
s/cluste\(r[^l][^(.]*\|r\)\.deregister_stake_pool(/cluste\1.g_stake_pool.deregister_stake_pool(/g

s/cluste\(r[^l][^(.]*\|r\)\.tx_era_arg/cluste\1.g_transaction.tx_era_arg/g
s/cluste\(r[^l][^(.]*\|r\)\.calculate_tx_ttl(/cluste\1.g_transaction.calculate_tx_ttl(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_txid(/cluste\1.g_transaction.get_txid(/g
s/cluste\(r[^l][^(.]*\|r\)\.view_tx(/cluste\1.g_transaction.view_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_hash_script_data(/cluste\1.g_transaction.get_hash_script_data(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_tx_deposit(/cluste\1.g_transaction.get_tx_deposit(/g
s/cluste\(r[^l][^(.]*\|r\)\.build_raw_tx_bare(/cluste\1.g_transaction.build_raw_tx_bare(/g
s/cluste\(r[^l][^(.]*\|r\)\.build_raw_tx(/cluste\1.g_transaction.build_raw_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.estimate_fee(/cluste\1.g_transaction.estimate_fee(/g
s/cluste\(r[^l][^(.]*\|r\)\.calculate_tx_fee(/cluste\1.g_transaction.calculate_tx_fee(/g
s/cluste\(r[^l][^(.]*\|r\)\.calculate_min_value(/cluste\1.g_transaction.calculate_min_value(/g
s/cluste\(r[^l][^(.]*\|r\)\.calculate_min_req_utxo(/cluste\1.g_transaction.calculate_min_req_utxo(/g
s/cluste\(r[^l][^(.]*\|r\)\.build_tx(/cluste\1.g_transaction.build_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.sign_tx(/cluste\1.g_transaction.sign_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.witness_tx(/cluste\1.g_transaction.witness_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.assemble_tx(/cluste\1.g_transaction.assemble_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.submit_tx_bare(/cluste\1.g_transaction.submit_tx_bare(/g
s/cluste\(r[^l][^(.]*\|r\)\.submit_tx(/cluste\1.g_transaction.submit_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.send_tx(/cluste\1.g_transaction.send_tx(/g
s/cluste\(r[^l][^(.]*\|r\)\.build_multisig_script(/cluste\1.g_transaction.build_multisig_script(/g
s/cluste\(r[^l][^(.]*\|r\)\.get_policyid(/cluste\1.g_transaction.get_policyid(/g
s/cluste\(r[^l][^(.]*\|r\)\.calculate_plutus_script_cost(/cluste\1.g_transaction.calculate_plutus_script_cost(/g
s/cluste\(r[^l][^(.]*\|r\)\.send_funds(/cluste\1.g_transaction.send_funds(/g
