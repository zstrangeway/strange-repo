/**
 * Liveness probe for the load balancer / App Runner health check.
 *
 * Deliberately does no downstream work: it answers "is this container able to
 * serve traffic", not "are its dependencies healthy".
 */
export async function GET(): Promise<Response> {
  return Response.json({ status: "ok" });
}
