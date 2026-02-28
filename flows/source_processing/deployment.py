from uuid import UUID

from prefect import flow

from settings import BASE_PATH, prefect_settings


async def deploy_process_source_flow(source_id: int) -> UUID:
    """Deploy the process source flow."""
    deployment = await flow.from_source(
        source=BASE_PATH,
        entrypoint="flows/source_processing/pipeline.py:process_source",
    )  # ty:ignore[invalid-await]

    return await deployment.deploy(
        name=f"PROCESS_SOURCE_{source_id}",
        work_pool_name=prefect_settings.pool_name,
        parameters={"source_id": source_id},
        concurrency_limit=1,
        print_next_steps=False,
        ignore_warnings=True,
    )
