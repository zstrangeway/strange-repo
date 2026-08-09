Feature: Health endpoint
  As the platform running example-web
  I want a health check the load balancer can poll
  So that only healthy containers receive traffic

  Scenario: The app reports that it is healthy
    When the health endpoint is called
    Then the health response status is 200
    And the reported status is "ok"
