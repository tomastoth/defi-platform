import os

import dotenv

dotenv.load_dotenv()


class Config:
    eth_rpc_url = os.getenv("ETH_RPC_URL")
    etherescan_key = os.getenv("ETHERSCAN_KEY")
    covalent_key = os.getenv("COVALENT_API_KEY")
    moralis_key = os.getenv("MORALIS_API_KEY")
    zapper_key = os.getenv("ZAPPER_API_KEY")
    root_dir = os.path.dirname(os.path.abspath(__file__)).replace("src", "")
    test_data_dir = os.path.join(root_dir, "tests", "test_data")


config = Config()
