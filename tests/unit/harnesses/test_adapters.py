"""Offline adapter contract tests; these do not certify tool authorization."""
import asyncio
from types import SimpleNamespace
import pytest
from enterprise_ai_patterns.harnesses.contracts import HarnessRequest
from enterprise_ai_patterns.harnesses.custom_adapter import CustomAgentLoopAdapter
from enterprise_ai_patterns.harnesses.langchain_adapter import LangChainHarnessAdapter
from enterprise_ai_patterns.harnesses.openai_agents_adapter import OpenAIAgentsAdapter


def request(tools=()):
    return HarnessRequest('task', 'session', 'caller', 'investigate order', tuple(tools), 3)


class FakeLoop:
    def __init__(self, fail=False): self.fail=fail; self.calls=[]
    async def run(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail: raise RuntimeError('backend unavailable')
        return 'finished'


@pytest.mark.parametrize('fail', [False, True])
def test_custom_adapter(fail):
    loop = FakeLoop(fail)
    result=asyncio.run(CustomAgentLoopAdapter(loop).run(request()))
    assert result.status == ('error' if fail else 'completed')
    assert result.error == ('RuntimeError' if fail else None)
    assert loop.calls == [{'session_id':'session','caller_id':'caller','goal':'investigate order'}]
    assert result.elapsed_ms >= 0


class FakeRunnable:
    def __init__(self, fail=False, messages=True): self.fail=fail; self.messages=messages; self.calls=[]
    async def ainvoke(self, payload, config=None):
        self.calls.append((payload,config))
        if self.fail: raise RuntimeError('model offline')
        return {'messages':[SimpleNamespace(content='answer')]} if self.messages else {'messages':[]}


def test_langchain_rejects_unknown_tool_without_model_call():
    runnable=FakeRunnable()
    result=asyncio.run(LangChainHarnessAdapter(runnable,tool_names=('lookup_order',)).run(request(('send_email',))))
    assert result.status=='denied' and runnable.calls==[]


@pytest.mark.parametrize('fail,has_messages,expected_status,expected_response',[
    (False,True,'completed','answer'),(False,False,'completed',''),(True,True,'error','')])
def test_langchain_invocation(fail,has_messages,expected_status,expected_response):
    runnable=FakeRunnable(fail,has_messages)
    result=asyncio.run(LangChainHarnessAdapter(runnable,tool_names=('lookup_order',)).run(request(('lookup_order',))))
    assert result.status==expected_status and result.response==expected_response
    assert runnable.calls[0][1]['configurable']['thread_id']=='session'
    if fail: assert result.error=='RuntimeError'


class FakeRunner:
    def __init__(self, fail=False): self.fail=fail; self.calls=[]
    async def run(self, agent, prompt, **kwargs):
        self.calls.append((agent,prompt,kwargs))
        if self.fail: raise RuntimeError('provider outage')
        return SimpleNamespace(final_output='order complete')


@pytest.mark.parametrize('fail',[False,True])
def test_openai_agents_invocation(fail):
    runner=FakeRunner(fail)
    agent=object()
    result=asyncio.run(OpenAIAgentsAdapter(agent,runner).run(request(('lookup_order',))))
    assert result.status==('error' if fail else 'completed')
    assert runner.calls==[(agent,'investigate order',{'max_turns':3})]
    assert result.error == ('RuntimeError' if fail else None)
    if not fail: assert result.response=='order complete'


def test_openai_adapter_does_not_enforce_allowed_tools_documented_limitation():
    runner=FakeRunner()
    result=asyncio.run(OpenAIAgentsAdapter(object(),runner).run(request(())))
    assert result.status=='completed'
    assert len(runner.calls)==1  # No security assertion: wrapper requires separate gateway.
