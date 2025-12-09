import logging
import sys
import os
import dotenv

# Configure root logging early so INFO/DEBUG appear.
# Default root level is WARNING, which hides INFO/DEBUG. basicConfig sets
# a handler and level so lower-severity messages are shown.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)

from .agents.agent_001.graph import Agent001
from .agents.agent_002.graph import Agent002
from .agents.agent_003.graph import Agent003

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

key = os.getenv("LANGSMITH_API_KEY")
if not key:
    raise ValueError("LANGSMITH_API_KEY not set in environment variables.")
logger.info("LANGSMITH_API_KEY found in environment variables: %s", key[:4] + "***")

if __name__ == "__main__":
    # agent_001 = Agent001("Pascal")
    # input_state_001 = {"user": "Alice"}
    # output_state_001 = agent_001.run(input_state_001)
    # logger.info(output_state_001)

    # agent_002 = Agent002("Pascal")
    # input_state_002 = {"user": "Bob", "question": "What is the capital of France?"}
    # output_state_002 = agent_002.run(input_state_002)
    # logger.info(output_state_002["answer"])

    agent_003 = Agent003("Pascal")
    input_state_003 = {"user": "Charlie", "question": "What is 7 multiplied by (3+2)?"}
    output_state_003 = agent_003.run(input_state_003)
    logger.info(output_state_003["answer"])