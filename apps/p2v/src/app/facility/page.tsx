import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = {
  title: "Our facility | P2V Basketball Academy",
  description:
    "Explore P2V Basketball Academy’s basketball training area and strength and conditioning space in Madison, Wisconsin.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="page-hero">
          <p className="eyebrow">THE FACILITY / P2V BASKETBALL ACADEMY</p>
          <h1>
            WHERE THE
            <br />
            <em>WORK HAPPENS.</em>
          </h1>
          <p className="intro">
            A place to sharpen your basketball skills and build the strength
            behind your game. Step inside P2V.
          </p>
        </section>
        <section
          className="section cream facility-section"
          aria-labelledby="court-title"
        >
          <figure className="facility-photo">
            <img
              src="/assets/facility-court-empty.jpg"
              alt="Inside P2V’s basketball training area, with multiple hoops, court markings, and training cones"
              width="1536"
              height="1152"
              fetchPriority="high"
            />
            <figcaption>01 / BASKETBALL TRAINING AREA</figcaption>
          </figure>
          <div className="facility-copy">
            <p className="eyebrow">ON THE COURT</p>
            <h2 id="court-title">
              Room to work
              <br />
              on your game.
            </h2>
            <p>
              The basketball area brings multiple hoops and space for drills
              into one training environment. From ball handling to shooting,
              it’s a place to put coaching into practice.
            </p>
            <ul className="facility-features">
              <li>Multiple baskets for shooting and finishing work</li>
              <li>Court space for ball handling and footwork drills</li>
              <li>Cones and training equipment for focused practice</li>
            </ul>
            <a className="button dark" href="/training.html">
              Explore basketball training
            </a>
          </div>
        </section>
        <section
          className="section facility-section facility-reverse"
          aria-labelledby="strength-title"
        >
          <figure className="facility-photo">
            <img
              src="/assets/facility-strength.jpg"
              alt="P2V’s strength and conditioning area with a weight rack, bench, battle ropes, and marked turf"
              width="1536"
              height="1152"
              loading="lazy"
            />
            <figcaption>02 / STRENGTH &amp; CONDITIONING AREA</figcaption>
          </figure>
          <div className="facility-copy">
            <p className="eyebrow">BEYOND THE COURT</p>
            <h2 id="strength-title">
              Build the athlete.
              <br />
              <em>Support the game.</em>
            </h2>
            <p>
              Alongside the basketball space, P2V has a dedicated area for
              strength and conditioning. Weights, ropes, and marked turf support
              the physical work that complements skill development.
            </p>
            <ul className="facility-features">
              <li>Weight rack, bench, and plates for strength work</li>
              <li>Marked turf for movement and conditioning drills</li>
              <li>Battle ropes and a variety of training equipment</li>
            </ul>
            <a className="button outline" href="/training.html#skills">
              See our training approach
            </a>
          </div>
        </section>
        <section
          className="section cream facility-visit"
          aria-labelledby="visit-title"
        >
          <div>
            <p className="eyebrow">YOUR FIRST VISIT</p>
            <h2 id="visit-title">
              Start with
              <br />a conversation.
            </h2>
            <p>
              Contact the coaches before your first session. They’ll help you
              find the right training option and confirm the time, location, and
              what to bring.
            </p>
            <div className="actions">
              <a className="button dark" href="/contact.html?interest=Training">
                Ask about your first session
              </a>
              <a className="textlink" href="/schedule.html">
                Plan your visit
              </a>
            </div>
          </div>
          <aside>
            <span className="small">BASED IN MADISON, WISCONSIN</span>
            <h3>Find your starting point.</h3>
            <p>
              Share your athlete’s age, experience, and goals so the coaches can
              recommend a fit.
            </p>
            <a className="textlink" href="mailto:p2vacademy@gmail.com">
              p2vacademy@gmail.com
            </a>
          </aside>
        </section>
      </main>
      <SiteFooter facility />
    </>
  );
}
