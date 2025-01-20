from solders.pubkey import Pubkey
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID

def get_associated_token_account(wallet_address: str, token_mint_address: str) -> str:
    """
    Compute the associated token account address for a given wallet and token mint.
    
    Args:
        wallet_address: The wallet address (EoA) as a base58 string
        token_mint_address: The token mint address as a base58 string
        
    Returns:
        The associated token account address as a base58 string
    """
    wallet_pubkey = Pubkey.from_string(wallet_address)
    token_mint_pubkey = Pubkey.from_string(token_mint_address)
    
    # Find PDA for associated token account
    associated_token_address, _ = Pubkey.find_program_address(
        seeds=[
            bytes(wallet_pubkey),
            bytes(TOKEN_PROGRAM_ID),
            bytes(token_mint_pubkey)
        ],
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID
    )
    
    return str(associated_token_address) 