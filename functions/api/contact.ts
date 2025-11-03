// Cloudflare Pages Function for contact form submissions
// Reads BREVOAPIKEY from environment (Pages → Settings → Environment variables)

interface ContactEnv {
  BREVOAPIKEY?: string;
  WORKING_MAIL?: string;
}

type PagesContext = {
  request: Request;
  env: ContactEnv;
};

export const onRequestPost = async ({ request, env }: PagesContext) => {
  const apiKey = env.BREVOAPIKEY;
  const toEmail = env.WORKING_MAIL || "info@ecoshacktasmania.com.au";

  if (!apiKey) {
    return new Response(
      JSON.stringify({ ok: false, error: "Missing BREVOAPIKEY in environment" }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  let name = "";
  let email = "";
  let subject = "Contact form submission";
  let message = "";

  const ct: string = request.headers.get("content-type") || "";
  try {
    if (ct.includes("application/json")) {
      const body = await request.json();
      name = (body.name ?? "").toString();
      email = (body.email ?? "").toString();
      subject = (body.subject ?? subject).toString();
      message = (body.message ?? "").toString();
    } else if (ct.includes("application/x-www-form-urlencoded")) {
      const text = await request.text();
      const params = new URLSearchParams(text);
      name = (params.get("name") ?? "").toString();
      email = (params.get("email") ?? "").toString();
      subject = (params.get("subject") ?? subject).toString();
      message = (params.get("message") ?? "").toString();
    } else if (ct.includes("multipart/form-data")) {
      const form = await request.formData();
      name = (form.get("name") ?? "").toString();
      email = (form.get("email") ?? "").toString();
      subject = (form.get("subject") ?? subject).toString();
      message = (form.get("message") ?? "").toString();
    } else {
      // Fallback: attempt to treat body as urlencoded
      const text = await request.text();
      const params = new URLSearchParams(text);
      name = (params.get("name") ?? "").toString();
      email = (params.get("email") ?? "").toString();
      subject = (params.get("subject") ?? subject).toString();
      message = (params.get("message") ?? "").toString();
    }
  } catch (err: any) {
    return new Response(
      JSON.stringify({ ok: false, error: err?.message || "Invalid request body" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  // Validation
  if (!name || !email || !message) {
    return new Response(
      JSON.stringify({ ok: false, error: "Missing required fields" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }
  const emailValid = /.+@.+\..+/.test(email);
  if (!emailValid) {
    return new Response(
      JSON.stringify({ ok: false, error: "Invalid email address" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  const htmlContent = `
    <div style="font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; line-height:1.6;">
      <h2 style="margin:0 0 12px;">New Contact Message</h2>
      <p><strong>Name:</strong> ${name}</p>
      <p><strong>Email:</strong> ${email}</p>
      <p><strong>Subject:</strong> ${subject}</p>
      <p><strong>Message:</strong></p>
      <div style="white-space:pre-wrap;">${message}</div>
      <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb;" />
      <p style="color:#6b7280;font-size:12px;">This email was sent via the Eco Shack website contact form.</p>
    </div>
  `;

  // Send via Brevo REST API (Workers-safe)
  const res = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "api-key": apiKey,
    },
    body: JSON.stringify({
      sender: { email: toEmail, name: "Eco Shack Website" },
      to: [{ email: toEmail, name: "Eco Shack" }],
      replyTo: { email, name },
      subject: subject || "New message from Eco Shack website",
      htmlContent,
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    return new Response(
      JSON.stringify({ ok: false, error: detail || "Brevo send error" }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }

  // If the request came from a standard browser form submit, redirect to success page
  const accept = (request.headers.get("accept") || "").toLowerCase();
  const wantsHtml = accept.includes("text/html") || accept.includes("application/xhtml+xml");
  if (wantsHtml) {
    return new Response(null, {
      status: 303,
      headers: { Location: "/contact-success" },
    });
  }

  // Default JSON response for programmatic clients
  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
};