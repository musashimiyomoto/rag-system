from pydantic import BaseModel, Field, computed_field


class ServiceHealthResponse(BaseModel):
    name: str = Field(description="Service name")
    status: bool = Field(description="Service status")


class HealthResponse(BaseModel):
    services: list[ServiceHealthResponse] = Field(
        default_factory=list, description="Services health status"
    )

    @computed_field
    def status(self) -> bool:
        """Status.

        Returns:
            True when all services are healthy.

        """
        return all(service.status for service in self.services)
