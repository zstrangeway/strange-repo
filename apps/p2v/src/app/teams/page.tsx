import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { CallToAction } from "@/components/call-to-action";

export const metadata: Metadata = {
  title: "P2V teams | P2V Basketball Academy",
  description:
    "P2V Basketball Academy in Madison, Wisconsin. Explore basketball training, skill camps, and competitive teams with Coach Will Turner.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="page-hero">
          <p className="eyebrow">P2V TEAMS / REPRESENTING THE 608</p>
          <h1>
            YOUR TEAM.
            <br />
            <em>YOUR NEXT STEP.</em>
          </h1>
          <p className="intro">
            Bring the work from training into team competition. Explore P2V’s
            14U and 16U programs and connect with the coaches about the next
            season.
          </p>
        </section>
        <section className="section cream">
          <div className="section-head">
            <div>
              <p className="eyebrow">THE TEAM PROGRAM</p>
              <h2>Find your next level.</h2>
            </div>
            <p>
              Ask the coaches about age eligibility, tryouts, roster
              availability, and the season schedule.
            </p>
          </div>
          <div className="team-grid">
            <article className="team">
              <span className="small">P2V BASKETBALL</span>
              <h2>
                14<span>U</span>
              </h2>
              <p>Build your game through teamwork and competition.</p>
              <a
                className="button dark"
                href="/contact.html?interest=14U%20Team"
              >
                14U inquiries
              </a>
            </article>
            <article className="team">
              <span className="small">P2V BASKETBALL</span>
              <h2>
                16<span>U</span>
              </h2>
              <p>Keep developing your skills and competing together.</p>
              <a
                className="button dark"
                href="/contact.html?interest=16U%20Team"
              >
                16U inquiries
              </a>
            </article>
          </div>
        </section>
        <section className="section competition detail-backdrop">
          <p className="eyebrow">THE COMPETITIVE STAGE</p>
          <h2>
            Local roots.
            <br />
            Midwest competition.
          </h2>
          <div className="circuit">
            <span>
              PUMA
              <br />
              <b>NXTPRO</b>
            </span>
            <p>
              COMPETING TOGETHER
              <br />
              ACROSS THE MIDWEST
            </p>
            <a className="button outline" href="/contact.html?interest=Tryouts">
              Ask about tryouts
            </a>
          </div>
        </section>
        <CallToAction />
      </main>
      <SiteFooter />
    </>
  );
}
