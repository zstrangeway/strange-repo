import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { CallToAction } from "@/components/call-to-action";

export const metadata: Metadata = {
  title: "Schedule & getting started | P2V Basketball Academy",
  description:
    "P2V Basketball Academy in Madison, Wisconsin. Explore basketball training, skill camps, and competitive teams with Coach Will Turner.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="page-hero">
          <p className="eyebrow">PLAN YOUR NEXT REP</p>
          <h1>
            MAKE TIME
            <br />
            <em>FOR YOUR GAME.</em>
          </h1>
          <p className="intro">
            Request current training times, camp dates, or team practice details
            directly from the coaching team.
          </p>
        </section>
        <section className="section cream schedule-grid">
          <div>
            <p className="eyebrow">TRAINING &amp; PRACTICE</p>
            <h2>
              Plan your
              <br />
              next session.
            </h2>
            <p>
              Tell the coaches which program you’re interested in and when
              you’re available. They’ll help you confirm the details for your
              next visit.
            </p>
            <a href="/contact.html?interest=Schedule" className="button dark">
              Request the schedule
            </a>
          </div>
          <aside className="schedule-info">
            <div>
              <span className="small">LOCATION</span>
              <h3>Madison, Wisconsin</h3>
              <p>
                Training takes place in the Madison area. Confirm your session’s
                location with the coaches before you arrive.
              </p>
              <a className="textlink" href="/facility.html">
                Take a look inside P2V
              </a>
            </div>
            <div>
              <span className="small">FIRST TIME AT P2V?</span>
              <h3>Connect before you arrive.</h3>
              <p>
                Share your athlete’s age, experience, and goals before your
                first session so the coaches can help you find the right fit.
              </p>
            </div>
          </aside>
        </section>
        <section className="section">
          <p className="eyebrow">A SIMPLE START</p>
          <div className="values">
            <div>
              <span>01</span>
              <h3>Tell us your goals.</h3>
              <p>
                Share your athlete’s age, experience, and what they want to work
                on.
              </p>
            </div>
            <div>
              <span>02</span>
              <h3>Find your fit.</h3>
              <p>Ask about training options, camps, or team opportunities.</p>
            </div>
            <div>
              <span>03</span>
              <h3>Confirm the details.</h3>
              <p>
                Check time, location, pricing, and what to bring with the
                coaching team.
              </p>
            </div>
          </div>
        </section>
        <CallToAction />
      </main>
      <SiteFooter />
    </>
  );
}
