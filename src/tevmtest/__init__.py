from __future__ import annotations

import time
import json
from pathlib import Path

import rlp
import requests

from rlp.sedes import (
    big_endian_int,
    binary,
    Binary
)

from leap.cleos import CLEOS
from leap.protocol import Asset

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from .utils import to_wei, to_int, decode_hex, remove_0x_prefix


EVM_CONTRACT = 'eosio.evm'
DEFAULT_GAS_PRICE = '0x01'
DEFAULT_GAS_LIMIT = '0x1e8480'
DEFAULT_VALUE = '0x00'
DEFAULT_DATA = '0x00'


address = Binary.fixed_length(20, allow_empty=True)


class EVMTransaction(rlp.Serializable):
    fields = [
        ('nonce', big_endian_int),
        ('gas_price', big_endian_int),
        ('gas', big_endian_int),
        ('to', address),
        ('value', big_endian_int),
        ('data', binary)
        # ('v', big_endian_int),
        # ('r', big_endian_int),
        # ('s', big_endian_int)
    ]

    def encode(self) -> bytes:
        return rlp.encode(self)


class CLEOSEVM(CLEOS):

    def __init__(
        self,
        *args,
        evm_chain_id: int = 41,
        evm_endpoint: str = 'http://localhost:9545',
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.evm_endpoint = evm_endpoint
        self.evm_chain_id = evm_chain_id

        self._w3 = Web3(Web3.HTTPProvider(evm_endpoint))

        self.evm_contracts = {}

        self.evm_default_account: LocalAccount = Account.from_key(
            '0x87ef69a835f8cd0c44ab99b7609a20b2ca7f1c8470af4f0e5b44db927d542084')

    @property
    def w3(self) -> Web3:
        return self._w3

    @staticmethod
    def default() -> CLEOSEVM:
        cleos = CLEOSEVM(
            endpoint='http://127.0.0.1:8890',
            evm_endpoint='http://127.0.0.1:9545',
            evm_chain_id=41
        )

        cleos.import_key('eosio', '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL')
        cleos.import_key('eosio.evm', '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL')

        cleos.load_abi_file('eosio.evm', 'tests/contracts/eosio.evm/regular/regular.abi')

        return cleos

    @staticmethod
    def from_cleos(other: CLEOS | CLEOSEVM) -> CLEOSEVM:
        if isinstance(other, CLEOSEVM):
            return other

        cleos = CLEOSEVM.default()

        for name in (
            'endpoint',
            'ship_endpoint',
            'node_dir',
            'keys',
            'private_keys',
            '_key_to_acc',
        ):
            setattr(cleos, name, getattr(other, name))

        return cleos


    def deploy_evm(
        self,
        contract_path: str | Path = Path('tests/contracts/eosio.evm/regular'),
        contract_name: str = 'regular',
        account_name: str = 'eosio.evm',
        start_bytes: int = 2684354560,
        start_cost: str = '21000.0000 TLOS',
        target_free: int = 2684354560,
        min_buy: int = 0,
        fee_transfer_pct: int = 100,
        gas_per_byte: int = 69,
        initial_revision: int = 0
    ):
        master_key = self.keys['eosio']

        # create evm accounts
        self.new_account(
            'eosio.evm',
            key=master_key,
            ram=start_bytes)

        self.new_account(
            'fees.evm',
            key=master_key,
            ram=100000)

        # ram_price_post = self.get_ram_price()

        # start_cost = Asset(ram_price_post.amount * start_bytes, sys_token)

        self.new_account(
            'rpc.evm',
            key=master_key,
            cpu='10000.0000 TLOS',
            net='10000.0000 TLOS',
            ram=100000)

        # self.create_snapshot({})
        target_deploy_block = 58
        self.wait_block(target_deploy_block - 3, interval=0.05)

        self.logger.info('deploying evm contract')

        self.evm_deploy_info = self.deploy_contract_from_path(
            account_name=account_name,
            contract_path=contract_path,
            contract_name=contract_name,
            privileged=True,
            create_account=False
        )

        actual_deploy_block = self.evm_deploy_info['processed']['block_num']
        if actual_deploy_block != target_deploy_block:
            raise ValueError(
                f'Contract failed to deploy at block {target_deploy_block}, actual: {actual_deploy_block}'
            )

        self.evm_init_info = self.push_action(
            'eosio.evm',
            'init',
            [
                start_bytes,
                start_cost,
                target_free,
                min_buy,
                fee_transfer_pct,
                gas_per_byte
            ],
            'eosio.evm'
        )

        self.wait_blocks(1)

        if initial_revision > 0:
            self.push_action(
                'eosio.evm', 'setrevision', [1], 'eosio.evm')

        self.wait_blocks(1)

        self.create_test_evm_account()

    def create_test_evm_account(
        self,
        name: str = 'evmuser1',
        data: str = 'foobar',
        truffle_addr: str = '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd'
    ):
        self.new_account(
            name,
            key=self.keys['eosio'])

        addr_amount_pairs = [
            (truffle_addr, 100000000),
            ('0xc51fE232a0153F1F44572369Cefe7b90f2BA08a5', 100000),
            ('0xf922CC0c6CA8Cdbf5330A295a11A40911FDD3B6e', 10000),
            ('0xCfCf671eBE5880d2D7798d06Ff7fFBa9bdA1bE64', 10000),
            ('0xf6E6c4A9Ca3422C2e4F21859790226DC6179364d', 10000),
            ('0xe83b5B17AfedDb1f6FF08805CE9A4d5eDc547Fa2', 10000),
            ('0x97baF2200Bf3053cc568AA278a55445059dF2d97', 10000),
            ('0x2e5A2c606a5d3244A0E8A4C4541Dfa2Ec0bb0a76', 10000),
            ('0xb4A541e669D73454e37627CdE2229Ad208d19ebF', 10000),
            ('0x717230bA327FE8DF1E61434D99744E4aDeFC53a0', 10000),
            ('0x52b7c04839506427620A2B759c9d729BE0d4d126', 10000)
        ]

        gas_allowance = 20

        total_needed = sum([q for a, q in addr_amount_pairs]) + gas_allowance

        self.create_evm_account(name, data)
        quantity = Asset.from_ints(total_needed * (10 ** 4), 4, 'TLOS')

        self.transfer_token('eosio', name, quantity, ' ')
        self.transfer_token(name, 'eosio.evm', quantity, 'Deposit')

        self.wait_blocks(3)

        eth_addr = self.eth_account_from_name(name)
        assert eth_addr

        self.logger.info(f'{name}: {eth_addr}')

        for addr, amount in addr_amount_pairs:
            self.eth_transfer_via_native(
                eth_addr,
                addr,
                Asset.from_ints(amount * (10 ** 4), 4, 'TLOS'),
                account='evmuser1'
            )


    """    eosio.evm interaction
    """

    def get_evm_config(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'config')

    def get_evm_resources(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'resources')

    def eth_account_from_name(self, name) -> str | None:
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            index_position=3,
            key_type='name',
            lower_bound=name,
            upper_bound=name
        )

        if len(rows) != 1:
            return None

        return f'0x{rows[0]["address"]}'

    def create_evm_account(
        self,
        account: str,
        salt: str
    ):
        return self.push_action(
            'eosio.evm',
            'create',
            [account, salt],
            account,
            key=self.get_private_key(account)
        )

    """ EVM
    """

    def wait_evm_block(self, block_num: int, progress: bool = False, interval: float = .5):
        current_block = self.w3.eth.block_number

        last_report = -1000
        def report():
            nonlocal last_report
            self.logger.info(f'waiting for block {block_num}, current: {current_block}, remaining: {block_num - current_block}')
            last_report = current_block

        while current_block < block_num:
            if current_block - last_report > 1000:
                report()

            time.sleep(interval)
            current_block = self.w3.eth.block_number

    def wait_evm_blocks(self, n: int, **kwargs):
        target_block = int(self.w3.eth.block_number) + n
        self.wait_evm_block(target_block, **kwargs)

    def eth_gas_price(self) -> int:
        config = self.get_evm_config()
        assert len(config) == 1
        config = config[0]
        assert 'gas_price' in config
        return to_int(hexstr=f'0x{config["gas_price"]}')

    def eth_get_balance(self, addr: str) -> int:
        addr = remove_0x_prefix(addr)
        addr = ('0' * (12 * 2)) + addr
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            index_position=2,
            key_type='sha256',
            lower_bound=addr,
            upper_bound=addr
        )

        if len(rows) != 1:
            return None

        return int(rows[0]['balance'], 16)


    def eth_get_transaction_count(self, addr: str) -> int:
        addr = remove_0x_prefix(addr)
        addr = ('0' * (12 * 2)) + addr
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            index_position=2,
            key_type='sha256',
            lower_bound=addr,
            upper_bound=addr
        )

        if len(rows) != 1:
            return None

        return rows[0]['nonce']

    def eth_get_transaction_receipt(self, transaction_hash, url=None):
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_getTransactionReceipt',
            'params': [transaction_hash],
            'id': 1
        }
        response = requests.post(
            url if url else self.evm_endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'})
        return response.json() if response.status_code == 200 else None

    def eth_get_code(self, address, block='latest', url=None):
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_getCode',
            'params': [address, block],
            'id': 1
        }
        response = requests.post(
            url if url else self.evm_endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'})
        return response.json() if response.status_code == 200 else None

    def eth_raw_tx(
        self,
        sender: str,
        data: str | bytes,
        gas: str,
        value: int,
        to: str | bytes
    ):
        if isinstance(gas, str):
            gas = to_int(hexstr=gas)

        nonce = self.eth_get_transaction_count(sender)
        gas_price = self.eth_gas_price()

        if isinstance(data, str):
            data = decode_hex(data)

        if isinstance(to, str):
            to = decode_hex(to)

        tx = EVMTransaction(
            nonce=nonce,
            gas_price=gas_price,
            gas=gas,
            to=to,
            value=value,
            data=data
        )

        return tx.encode()

    def eth_transfer_via_native(
        self,
        sender: str,  # eth addr
        to: str,  # eth addr
        quantity: Asset | str,
        account: str = 'eosio',
        estimate_gas: bool = False
    ):
        if isinstance(quantity, str):
            quantity = Asset.from_str(quantity)

        amount = quantity.amount // (10 ** quantity.symbol.precision)

        raw_tx = self.eth_raw_tx(
            sender,
            '',
            DEFAULT_GAS_LIMIT,
            to_wei(amount, 'ether'),
            to
        )

        self.logger.info('doing eth transfer...')
        self.logger.info(json.dumps({
            'account': account,
            'sender': sender,
            'to': to,
            'quantity': amount,
            'wei': to_wei(amount, 'ether')
        }, indent=4))

        sender = remove_0x_prefix(sender)

        return self.push_action(
            EVM_CONTRACT,
            'raw',
            [
                account,
                raw_tx,
                estimate_gas,
                sender
            ],
            account,
            key=self.get_private_key(account)
        )

    def eth_withdraw(self,
        quantity: str,
        to: str,
        account: str | None = None,
    ):
        if not account:
            account = to

        return self.push_action(
            EVM_CONTRACT,
            'withdraw',
            [to, quantity],
            account,
            key=self.get_private_key(account)
        )

    def eth_get_block_by_number(
        self,
        block_number: int | str,
        full_transactions: bool= False,
        url: str | None = None
    ):
        headers = {'Content-Type': 'application/json'}
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_getBlockByNumber',
            'params': [
                block_number,
                full_transactions
            ],
            'id': 1
        }
        response = requests.post(
            url if url else self.evm_endpoint,
            json=payload, headers=headers)
        return response.json() if response.status_code == 200 else None

    def eth_deploy_contract(
        self,
        contract_cls,
        contract_abi,
        contract_name: str,
        constructor_arguments: list[str] = [],
        account: Account | None = None,
        max_gas: int = int(1e8)
    ):
        # create deploy tx
        tx_args = {
            'from': account.address,
            'gas': max_gas,
            'gasPrice': self._w3.eth.gas_price,
            'nonce': self._w3.eth.get_transaction_count(account.address)
        }

        tx = contract_cls.constructor(*constructor_arguments).build_transaction(tx_args)

        signed_tx = account.sign_transaction(tx)

        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        tx_receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)

        _contract = self._w3.eth.contract(
            address=tx_receipt['contractAddress'], abi=contract_abi)

        self.evm_contracts[contract_name] = _contract

        return _contract, tx_receipt

    def eth_deploy_contract_from_files(
        self,
        abi_path: str | Path,
        bin_path: str | Path,
        contract_name: str,
        constructor_arguments: list[str] = [],
        account: Account | None = None,
        max_gas: int = int(1e8)
    ):
        if not isinstance(account, Account):
            account = self.evm_default_account

        with open(abi_path, 'r') as abi_fp:
            contract_abi = json.load(abi_fp)

        with open(bin_path, 'r') as bin_fp:
            contract_bin = bin_fp.read().strip()

        # instantiate
        Contract = self._w3.eth.contract(
            abi=contract_abi,
            bytecode=contract_bin
        )

        return self.eth_deploy_contract(
            Contract, contract_abi, contract_name,
            constructor_arguments=constructor_arguments,
            account=account,
            max_gas=max_gas
        )

    def eth_deploy_contract_from_json(
        self,
        contract_path: str | Path,
        contract_name: str,
        constructor_arguments: list[str] = [],
        account: LocalAccount | None = None,
        max_gas: int = int(1e8)
    ):
        if not isinstance(account, LocalAccount):
            account = self.evm_default_account

        with open(contract_path, 'r') as contract_fp:
            contract_interface = json.load(contract_fp)

        # instantiate
        Contract = self._w3.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bytecode']
        )

        return self.eth_deploy_contract(
            Contract, contract_interface['abi'], contract_name,
            constructor_arguments=constructor_arguments,
            account=account,
            max_gas=max_gas
        )

    def eth_build_and_send_transaction(self, function_call, eth_address, gas, gas_price, check_for_success=True):
        tx_args = {
            'from': eth_address.address,
            'gas': gas,
            'gasPrice': gas_price,
            'nonce': self.w3.eth.get_transaction_count(eth_address.address),
            'chainId': self.evm_chain_id
        }

        trx = function_call.build_transaction(tx_args)
        signed_trx = Account.sign_transaction(trx, eth_address.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_trx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        # self.wait_evm_block(receipt['blockNumber'] + 1)
        if check_for_success and receipt['status'] != 1:
            raise Exception(f"Transaction failed: {tx_hash.hex()}")

        return receipt

    def eth_transfer(self, sender, to, wei):
        tx_args = {
            'from': sender.address,
            'to': to,
            'gas': 80000,
            'gasPrice': DEFAULT_GAS_PRICE,
            'nonce': self.w3.eth.get_transaction_count(sender.address),
            'chainId': self.evm_chain_id,
            'value': wei
        }

        transfer_signed_trx = Account.sign_transaction(tx_args, sender.key)
        transfer_tx_hash = self.w3.eth.send_raw_transaction(transfer_signed_trx.raw_transaction)
        transfer_receipt = self.w3.eth.wait_for_transaction_receipt(transfer_tx_hash)
        if transfer_receipt['status'] != 1:
            raise Exception(f"Transaction failed: {transfer_tx_hash.hex()}")

        return transfer_receipt

    def delegate_bandwidth(
            self,
            _from: str,
            _to: str,
            net: str,
            cpu: str,
            transfer: bool = True
    ):
        return self.push_action(
            'eosio',
            'delegatebw',
            [
                _from,
                _to,
                net,
                cpu,
                transfer
            ],
            _from,
            self.get_private_key(_from),
            'active'
        )
