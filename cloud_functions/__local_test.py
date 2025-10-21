import base64
import json


def trigger_cloud_run_job(event, context):
    """
    Cloud func entrypoint for Pub/Sub trigger
    """
    msg = base64.b64decode(event["data"]).decode("utf-8")
    payload = json.loads(msg)

    if payload.get("task") != "run_daily_payment_check":
        return

    local = True
    if local:
        import subprocess

        subprocess.run(["python", "-m", "pdb", "pubsub_workers/stripe/due_payments.py"])
    else:
        # Cloud func jon name reference
        job_name = (
            "projects/partyup-be-aaf0d/locations/REGION/jobs/daily-payment-check-job"
        )
        client = run_v2.JobsClient()
        client.run_job(name=job_name)


def simulate_pubsub_trigger():
    msg = {"task": "run_daily_payment_check",}
    event = {"data": base64.b64encode(json.dumps(msg).encode()).decode(),}
    context = None

    trigger_cloud_run_job(event=event, context=context)

if __name__ == "__main__":
    simulate_pubsub_trigger()
