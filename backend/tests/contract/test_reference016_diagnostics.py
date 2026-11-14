from types import SimpleNamespace

from tests.fakes.reference_api import install_model, send, last


def test_diagnostic_submission_failure_does_not_change_answer_or_history(client, auth_headers):
    graph, _, _ = install_model(client)
    class BrokenRecorder:
        def submit(self, data):
            raise OSError('private-diagnostic-storage')
    client.app.state.services.pipeline.diagnostics = BrokenRecorder()
    stream = send(client, auth_headers)
    assert last(stream, 'complete')['status'] == 'completed'
    assert graph.get_state('reference').values['messages'][-1].content.startswith('Final answer')
    assert 'private-diagnostic' not in str(stream)
    assert any(name == 'node' and data['node'] == 'diagnostics' and data['details']['diagnostic_status'] == 'failed'
               for name, data in stream)


def test_diagnostic_receipt_is_queued_without_claiming_saved(client, auth_headers):
    install_model(client)
    class QueuedRecorder:
        def submit(self, data):
            return SimpleNamespace(job_id='diagnostic-test', status='queued', reason='accepted')
    client.app.state.services.pipeline.diagnostics = QueuedRecorder()
    stream = send(client, auth_headers)
    receipt = next(data['details'] for name, data in stream if name == 'node' and data['node'] == 'diagnostics')
    assert receipt['diagnostic_id'] == 'diagnostic-test' and receipt['diagnostic_status'] == 'queued'
    assert not any(data.get('details', {}).get('diagnostic_status') == 'saved' for _, data in stream)
    assert stream[-1][0] == 'complete'
