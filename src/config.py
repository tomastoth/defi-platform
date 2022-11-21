import os

import dotenv

dotenv.load_dotenv()


class Config:
    eth_rpc_url = os.getenv("ETH_RPC_URL")
    etherescan_key = os.getenv("ETHERSCAN_KEY")
    db_url = os.getenv("DB_URL")
    covalent_key = os.getenv("COVALENT_API_KEY")
    root_dir = os.path.dirname(os.path.abspath(__file__)).replace("src", "")
    test_data_dir = root_dir + "\\tests" + "\\test_data"


config = Config()
