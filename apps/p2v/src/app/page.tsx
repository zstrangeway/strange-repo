import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { CallToAction } from "@/components/call-to-action";
import { Pillars } from "@/components/pillars";

export const metadata: Metadata = {
  title: "Basketball training in Madison | P2V Basketball Academy",
  description:
    "P2V Basketball Academy in Madison, Wisconsin. Explore basketball training, skill camps, and competitive teams with Coach Will Turner.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="forged-hero">
          <img
            className="forged-bg"
            src="/assets/forged-action.jpg"
            alt="Placeholder basketball photograph of a young athlete practicing a crossover in a dramatic indoor gym"
            fetchPriority="high"
          />
          <div className="hero-shade"></div>
          <div className="forged-copy">
            <p className="eyebrow">
              <span className="dot"></span> MADISON, WI · REPRESENTING THE 608
            </p>
            <h1>
              MORE THAN
              <br />
              <em>BASKETBALL.</em>
            </h1>
            <p className="intro">
              Build your game. Grow your character. Find your path.
            </p>
            <div className="actions">
              <a className="button" href="/training.html">
                Find your training
              </a>
              <a className="textlink" href="/about.html">
                Meet Coach Will
              </a>
            </div>
          </div>
        </section>
        <Pillars />
        <section className="programs-section compact-programs">
          <h2>
            YOUR GAME.
            <br />
            <em>YOUR PATH.</em>
          </h2>
          <div className="programs">
            <a className="program" href="/training.html#skills">
              <img
                className="program-photo"
                src="/assets/forged-action.jpg"
                alt="Placeholder photograph of an athlete practicing basketball"
                loading="lazy"
              />
              <span className="card-link">Training</span>
            </a>
            <a className="program" href="/training.html#camps">
              <img
                className="program-photo"
                src="/assets/camps.jpg"
                alt="Placeholder photograph of a basketball skill drill"
                loading="lazy"
              />
              <span className="card-link">Skill Camps</span>
            </a>
            <a className="program" href="/teams.html">
              <img
                className="program-photo"
                src="/assets/teams.jpg"
                alt="Placeholder photograph of basketball teammates in a huddle"
                loading="lazy"
              />
              <span className="card-link">P2V Teams</span>
            </a>
          </div>
        </section>
        <section className="coach section">
          <div className="coach-photo">
            <img
              src="/assets/coach.jpg"
              alt="Coach Will Turner, founder and head trainer of P2V"
              loading="lazy"
            />
            <span>COACH WILL TURNER / FOUNDER &amp; HEAD TRAINER</span>
          </div>
          <div className="coach-copy">
            <p className="eyebrow">A COACH IN YOUR CORNER</p>
            <h2>
              Building players.
              <br />
              <em>Shaping people.</em>
            </h2>
            <p>
              Coach Will Turner has spent years helping young athletes develop
              their game in Madison and across Dane County.
            </p>
            <p>
              His approach pairs skill development with mental toughness and
              character. Every challenge is a chance to learn, build confidence,
              and keep improving.
            </p>
            <a className="textlink" href="/about.html">
              The story behind P2V
            </a>
          </div>
        </section>
        <section className="competition section detail-backdrop">
          <p className="eyebrow">LOCAL ROOTS. BIGGER STAGE.</p>
          <div className="section-head">
            <h2>
              Made in Madison.
              <br />
              Tested in competition.
            </h2>
            <p>
              P2V teams compete on the PUMA NXTPRO circuit and at tournaments
              across the Midwest.
            </p>
          </div>
          <div className="circuit">
            <span>
              PUMA
              <br />
              <b>NXTPRO</b>
            </span>
            <p>
              THE NEXT LEVEL
              <br />
              STARTS WITH THE NEXT REP.
            </p>
            <a href="/teams.html" className="button outline">
              Explore our teams
            </a>
          </div>
        </section>
        <CallToAction />
      </main>
      <SiteFooter />
    </>
  );
}
