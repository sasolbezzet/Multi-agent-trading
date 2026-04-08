import os
def load_env():
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    print("Environment loaded")
