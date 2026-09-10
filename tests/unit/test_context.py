import pytest
from pihu.context.engine import ContextEngine

def test_environment_context_gathering():
    engine = ContextEngine()
    env = engine.get_environment_context()

    assert env.os != ""
    assert env.cwd != ""
    assert env.datetime_utc != ""

def test_project_context_gathering():
    engine = ContextEngine()
    proj = engine.get_project_context()

    assert proj.project_root != ""
    assert "Python" in proj.project_type or "Go" in proj.project_type

def test_render_system_context_prompt():
    engine = ContextEngine()
    prompt = engine.render_system_context_prompt()

    assert "ENVIRONMENT & PROJECT CONTEXT" in prompt
    assert "Operating System:" in prompt
    assert "Project Type:" in prompt
