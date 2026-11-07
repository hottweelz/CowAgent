"""Host-operator task inspection/retry; unavailable to restricted workers.

python -m agent.recovery list --owner AGENT
python -m agent.recovery show TASK_ID --owner AGENT
python -m agent.recovery cancel TASK_ID --owner AGENT
python -m agent.recovery retry TASK_ID --owner AGENT --acknowledge-effects
python -m agent.recovery verify TASK_ID --owner AGENT
"""
import argparse
import json


def main(argv=None, *, store=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('list', 'show', 'cancel', 'retry', 'verify'))
    parser.add_argument('task_id', nargs='?')
    parser.add_argument('--owner', required=True, help='Owning agent ID; must match the persisted task')
    parser.add_argument('--acknowledge-effects', action='store_true',
                        help='Acknowledge that explicit retry may repeat a previously completed effect')
    args = parser.parse_args(argv)
    if args.action != 'list' and not args.task_id:
        parser.error('task_id is required')
    try:
        if store is None:
            from config import load_config
            load_config()
            from agent.recovery.runtime import get_task_store
            store = get_task_store()
        if args.action == 'list':
            from agent.recovery.verification import outcome_summary
            result = [{**{k: row[k] for k in ('task_id', 'kind', 'state', 'attempt_count', 'reason')},
                       **outcome_summary(row)}
                      for row in store.list_tasks(owner_id=args.owner)]
        else:
            task = store.get(args.task_id)
            if task['owner_id'] != args.owner:
                raise ValueError('Task owner mismatch')
            if args.action == 'show':
                from agent.recovery.verification import outcome_summary
                result = dict(task, outcomes=outcome_summary(task))
            elif args.action == 'verify':
                from agent.recovery.verification import verify_task, outcome_summary
                task = verify_task(store, args.task_id, force=True)
                result = dict(task, outcomes=outcome_summary(task))
            elif args.action == 'cancel':
                store.request_stop(args.task_id)
                result = {'task_id': args.task_id, 'state': store.get(args.task_id)['state']}
            else:
                task = store.retry(args.task_id, acknowledge_effects=args.acknowledge_effects)
                result = {'task_id': args.task_id, 'state': task['state'],
                          'notice': 'Queued for the running CowAgent recovery service'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        # Operator needs the fixed state error, never raw task/config content.
        allowed = {'Task owner mismatch', 'task still owned by a live execution',
                   'retry requires acknowledgement of prior effects',
                   'Verification is busy', 'Task execution not completed', 'task execution not completed',
                   'task cannot be retried in its current state'}
        print(json.dumps({'error': str(exc) if str(exc) in allowed else 'Task journal operation failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
