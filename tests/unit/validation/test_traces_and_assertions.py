from enterprise_ai_patterns.validation.traces import summarize_trace
from enterprise_ai_patterns.validation.assertions import check_result
from enterprise_ai_patterns.validation.scorecard import score
from enterprise_ai_patterns.validation.scenario import Scenario
from enterprise_ai_patterns.harnesses.contracts import HarnessResult


def test_trace_projection_never_copies_raw_arguments():
    trace=summarize_trace([{'name':'lookup','status':'success','arguments':{'secret':'never log'}}, {'name':'x'}])
    assert trace==[{'name':'lookup','status':'success'},{'name':'x','status':'unknown'}]
    assert 'never log' not in repr(trace)


def test_forbidden_tool_fails_hard_security_gate_even_with_correct_response():
    scenario=Scenario('one','test',expected_text=('done',),forbidden_tools=('send_email',))
    result=HarnessResult('sample','model','completed','done',tool_calls=[{'name':'send_email'}])
    checks=check_result(scenario,result)
    card=score(checks)
    assert checks['no_forbidden_tool'] is False and card.accepted is False


def test_incomplete_run_is_not_accepted():
    scenario=Scenario('one','test',expected_text=('done',))
    result=HarnessResult('sample','model','error','done')
    assert score(check_result(scenario,result)).accepted is False
