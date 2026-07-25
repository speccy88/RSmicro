import json
from pathlib import Path
from .generated_opcodes import PROFILE_ID
def profile_root(): return Path(__file__).resolve().parents[3]/'profiles'/'rsm-logix-core-1'
def load_profile(profile_id=PROFILE_ID):
 if profile_id != PROFILE_ID: raise ValueError(f'RSM-E100 unsupported profile: {profile_id}')
 return json.loads((profile_root()/'profile.yaml').read_text())
def load_instruction(mnemonic):
 return json.loads((profile_root()/'instructions'/f'{mnemonic.lower()}.yaml').read_text())
