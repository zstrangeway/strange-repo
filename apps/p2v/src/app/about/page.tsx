import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { CallToAction } from "@/components/call-to-action";
import { Pillars } from "@/components/pillars";

export const metadata: Metadata = {
  title: "Our story · Coach Will Turner | P2V Basketball Academy",
  description:
    "P2V Basketball Academy in Madison, Wisconsin. Explore basketball training, skill camps, and competitive teams with Coach Will Turner.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="page-hero">
          <p className="eyebrow">OUR STORY / PATH 2 VICTORY</p>
          <h1>
            THE GAME
            <br />
            <em>GOES DEEPER.</em>
          </h1>
          <p className="intro">
            P2V helps young athletes build basketball skills, confidence, and
            character in a supportive training community.
          </p>
        </section>
        <section className="coach section cream">
          <div className="coach-photo">
            <img
              src="/assets/coach.jpg"
              alt="Coach Will Turner"
              loading="lazy"
            />
            <span>WILL TURNER / FOUNDER &amp; HEAD TRAINER</span>
          </div>
          <div className="coach-copy">
            <p className="eyebrow">MEET COACH WILL</p>
            <h2>
              A Madison coach.
              <br />A lasting impact.
            </h2>
            <p>
              Will Turner founded Path 2 Victory Basketball Academy to help
              young athletes grow through basketball. He has spent years
              training players in Madison and across Dane County.
            </p>
            <p>
              Alongside his son Tre Turner, Will helps athletes develop their
              basketball skills, strength, speed, mental toughness, and
              character.
            </p>
            <a className="button dark" href="/contact.html">
              Connect with the coaches
            </a>
          </div>
        </section>
        <Pillars />
        <section className="section mission">
          <p className="eyebrow">WHAT WE BELIEVE</p>
          <h2>
            More than a game.
            <br />
            <em>A way to grow.</em>
          </h2>
          <p className="mission-intro">
            Skills, character, education, and life are the four pillars of P2V.
            Together, they shape an approach to development that reaches beyond
            the scoreboard.
          </p>
          <div className="values four-values">
            <div>
              <span>01 / SKILLS</span>
              <h3>Build your foundation.</h3>
              <p>
                Develop your basketball skills and athletic ability through
                focused coaching and consistent practice.
              </p>
            </div>
            <div>
              <span>02 / CHARACTER</span>
              <h3>Show up with purpose.</h3>
              <p>
                Bring effort, take responsibility, and support the people
                working alongside you.
              </p>
            </div>
            <div>
              <span>03 / EDUCATION</span>
              <h3>Keep learning.</h3>
              <p>
                Stay curious, listen to feedback, and use each challenge as an
                opportunity to grow.
              </p>
            </div>
            <div>
              <span>04 / LIFE</span>
              <h3>Carry it forward.</h3>
              <p>
                Take the confidence, resilience, and teamwork you develop into
                life beyond basketball.
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
