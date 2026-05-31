export async function onRequestPost(context) {
  const body = await context.request.json();

  const titles = (body.searchTitles || "")
    .split(/\n|OR/i)
    .map(v => v.trim())
    .filter(Boolean);

  const results = titles.map((title, i) => ({
    id: String(i + 1),
    title,
    company: "Example Company",
    location: "Los Angeles, CA",
    site: "Cloudflare",
    pay: "$60,000 - $85,000",
    posted: "1 hour ago",
    term: title,
    remote: "No",
    job_type: "Full-time",
    company_url: "https://example.com",
    job_url: "https://example.com/job",
    description: `Mock result for ${title}`
  }));

  return new Response(
    JSON.stringify({
      ok: true,
      location: {
        display_name: "Los Angeles, CA"
      },
      results
    }),
    {
      headers: {
        "Content-Type": "application/json"
      }
    }
  );
}
