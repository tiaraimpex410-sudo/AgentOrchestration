import pytest
import tempfile
import shutil
from pathlib import Path
from src.agent.sandbox import AgentSandbox, ResourceLimits


class TestAgentSandbox:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_ao_sandbox_base_")
        self.sandbox = AgentSandbox(self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.sandbox.cleanup_all()

    def test_create_sandbox_success(self):
        """Verify that a safe, standard agent_id successfully creates an isolated sandbox."""
        agent_id = "agent-abc-123"
        path = self.sandbox.create(agent_id)
        
        assert path.exists()
        assert path.is_dir()
        assert path.name == agent_id
        assert str(path.parent.resolve()) == str(Path(self.temp_dir).resolve())

    def test_create_sandbox_sanitization_ignores_bad_chars(self):
        """Verify that non-alphanumeric/dash/underscore characters are stripped and creation succeeds."""
        agent_id = "agent@abc!123"
        expected_sanitized = "agentabc123"
        path = self.sandbox.create(agent_id)
        
        assert path.exists()
        assert path.is_dir()
        assert path.name == expected_sanitized
        
        # Verify lookup and destroy work with the original ID (via sanitization)
        assert self.sandbox.get_path(agent_id) == path
        assert self.sandbox.destroy(agent_id) is True

    def test_create_sandbox_empty_or_only_invalid_id_raises_value_error(self):
        """Verify that empty IDs or IDs consisting only of invalid characters raise a ValueError."""
        with pytest.raises(ValueError, match="agent_id cannot be empty|invalid characters"):
            self.sandbox.create("")

        with pytest.raises(ValueError, match="agent_id contains invalid characters"):
            self.sandbox.create("!@#$%^")

    def test_create_sandbox_confinement_violation_raises_value_error(self):
        """Verify that path traversal sequences (like ../) are blocked and raise ValueError."""
        with pytest.raises(ValueError, match="invalid characters|Confinement violation|directory traversal"):
            # If sanitization strips the bad characters
            # e.g., "../bad" becomes "bad", which is safe, but ".." becomes ValueError
            self.sandbox.create("..")

        with pytest.raises(ValueError, match="invalid characters|Confinement violation|directory traversal"):
            self.sandbox.create("../../escape")

    def test_get_path_and_destroy_sanitization(self):
        """Verify lookup and cleanup methods correctly sanitize inputs."""
        agent_id = "agent#test"
        sanitized = "agenttest"
        path = self.sandbox.create(agent_id)
        
        assert self.sandbox.get_path(agent_id) == path
        assert self.sandbox.get_path(sanitized) == path
        
        assert self.sandbox.destroy(agent_id) is True
        assert self.sandbox.get_path(agent_id) is None
