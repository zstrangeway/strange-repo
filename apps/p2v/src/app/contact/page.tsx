import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { InquiryForm } from "@/components/inquiry-form";

export const metadata: Metadata = {
  title: "Get started · Training & tryout inquiries | P2V Basketball Academy",
  description:
    "P2V Basketball Academy in Madison, Wisconsin. Explore basketball training, skill camps, and competitive teams with Coach Will Turner.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="page-hero contact-hero">
          <p className="eyebrow">GET STARTED / YOUR PATH 2 VICTORY</p>
          <h1>
            LET’S GET
            <br />
            <em>TO WORK.</em>
          </h1>
          <p className="intro">
            Tell the coaches what you’re looking for. Ask about training, camps,
            team opportunities, or session times.
          </p>
        </section>
        <section className="section cream contact-layout">
          <aside>
            <p className="eyebrow">A COACH IN YOUR CORNER</p>
            <h2>
              Your game.
              <br />
              Your next step.
            </h2>
            <p>
              Not sure where to start? Share your athlete’s experience and
              goals, and ask the coaches which option could be a good fit.
            </p>
            <a className="textlink" href="mailto:p2vacademy@gmail.com">
              p2vacademy@gmail.com
            </a>
            <div className="contact-note">
              <span className="small">HOW THIS WORKS</span>
              <p>
                Create a message below, review it, then send it through your
                email app. The coaches can help with availability and
                registration.
              </p>
            </div>
          </aside>
          <InquiryForm />
        </section>
        <section className="section faq">
          <p className="eyebrow">BEFORE YOU GET STARTED</p>
          <h2>Good to know.</h2>
          <details>
            <summary>How do I find the right training option?</summary>
            <p>
              Share your athlete’s age, experience, and goals with the coaches.
              They can explain current options and help identify a fit.
            </p>
          </details>
          <details>
            <summary>Where does P2V train?</summary>
            <p>
              P2V is based in Madison, Wisconsin. The coaches will confirm the
              location for your training session, camp, or team practice.
            </p>
          </details>
          <details>
            <summary>How do I get dates and pricing?</summary>
            <p>
              Ask the coaching team for the current schedule, pricing,
              availability, and camp or tryout details.
            </p>
          </details>
          <details>
            <summary>Does this form register my athlete?</summary>
            <p>
              No. It prepares an email inquiry. The coaching team will explain
              any registration steps directly.
            </p>
          </details>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
