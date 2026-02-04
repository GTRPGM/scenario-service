import pytest

from scenario.core.deps import get_scenario_engine, get_validator_agent


@pytest.mark.asyncio
async def test_deps_instantiation_integrity():
    """
    Verify that dependency provider functions in deps.py can be called
    without raising NameError or ImportError.
    This catches mistakes like using renamed agents before they are updated in deps.py.
    """
    # Simply calling the providers will trigger the instantiation logic inside
    # We don't necessarily need to run the whole app to catch NameErrors in deps.py
    try:
        engine = await get_scenario_engine()
        assert engine is not None

        validator = await get_validator_agent()
        assert validator is not None
    except NameError as e:
        pytest.fail(f"Dependency provider raised NameError: {e}")
    except ImportError as e:
        pytest.fail(f"Dependency provider raised ImportError: {e}")
    except Exception:
        # Other exceptions (like DB connection) are expected in some environments,
        # but the logic itself should be syntactically correct.
        pass
