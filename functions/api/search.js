export async function onRequestPost(context) {
  return new Response(
    JSON.stringify({
      ok: true,
      location: {
        display_name: "Los Angeles, CA"
      },
      results: [
        {
          id: "1",
          title: "Desktop Support Technician",
          company: "Example Company",
          location: "Los Angeles, CA",
          site: "Cloudflare",
          pay: "$60,000 - $85,000",
          posted: "1 hour ago",
          term: "desktop support",
          remote: "No",
          job_type: "Full-time",
          company_url: "https://example.com",
          job_url: "https://example.com/job",
          description: "Test result"
        }
      ]
    }),
    {
      headers: {
        "Content-Type": "application/json"
      }
    }
  );
}
