import type { APIRoute } from "astro";
import config from "@/config/config.json";
import Brevo from "@getbrevo/brevo";

function isValidEmail(email: string) {
  return /.+@.+\..+/.test(email);
}

export const POST: APIRoute = async ({ request }) => {
  try {
    const apiKey = import.meta.env.BREVOAPIKEY as string | undefined;
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

    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const body = await request.json();
      name = (body.name ?? "").toString();
      email = (body.email ?? "").toString();
      subject = (body.subject ?? subject).toString();
      message = (body.message ?? "").toString();
    } else {
      const form = await request.formData();
      name = (form.get("name") ?? "").toString();
      email = (form.get("email") ?? "").toString();
      subject = (form.get("subject") ?? subject).toString();
      message = (form.get("message") ?? "").toString();
    }

    // Basic validation
    if (!name || !email || !message) {
      return new Response(
        JSON.stringify({ ok: false, error: "Missing required fields" }),
        { status: 400, headers: { "content-type": "application/json" } },
      );
    }
    if (!isValidEmail(email)) {
      return new Response(
        JSON.stringify({ ok: false, error: "Invalid email address" }),
        { status: 400, headers: { "content-type": "application/json" } },
      );
    }

    // Prepare Brevo transactional email
    const api = new Brevo.TransactionalEmailsApi();
    api.setApiKey(Brevo.TransactionalEmailsApiApiKeys.apiKey, apiKey);

    const sendSmtpEmail = new Brevo.SendSmtpEmail();
    sendSmtpEmail.to = [
      { email: config.params.email, name: "Eco Shack" },
    ];
    sendSmtpEmail.sender = {
      email: config.params.email,
      name: "Eco Shack Website",
    };
    sendSmtpEmail.replyTo = { email, name };
    sendSmtpEmail.subject = subject || "New message from Eco Shack website";
    sendSmtpEmail.htmlContent = `
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

    try {
      await api.sendTransacEmail(sendSmtpEmail);
    } catch (err: any) {
      const detail = err?.body || err?.message || "Brevo send error";
      return new Response(
        JSON.stringify({ ok: false, error: detail }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }

    return new Response(
      JSON.stringify({ ok: true }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  } catch (error: any) {
    return new Response(
      JSON.stringify({ ok: false, error: error?.message || "Unexpected error" }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }
};