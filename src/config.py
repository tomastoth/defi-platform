import os
import dotenv

dotenv.load_dotenv()


class Config:
    eth_rpc_url = os.getenv("ETH_RPC_URL")
    etherescan_key = os.getenv("ETHERSCAN_KEY")
    db_url = os.getenv("DB_URL")
    covalent_key = os.getenv("COVALENT_API_KEY")


config = Config()
