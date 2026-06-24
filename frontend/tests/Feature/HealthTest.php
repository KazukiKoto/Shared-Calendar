<?php

namespace Tests\Feature;

use Tests\TestCase;

class HealthTest extends TestCase
{
    public function test_health_endpoint_returns_ok(): void
    {
        $response = $this->get('/health');

        $response->assertStatus(200);
        $response->assertJson(['status' => 'ok', 'service' => 'frontend']);
    }

    public function test_up_endpoint_returns_200(): void
    {
        $response = $this->get('/up');

        $response->assertStatus(200);
    }
}
