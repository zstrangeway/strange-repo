import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { CallToAction } from "@/components/call-to-action";
import { TrainingTabs } from "@/components/training-tabs";

export const metadata: Metadata = {
  title: "Training & skill camps | P2V Basketball Academy",
  description:
    "P2V Basketball Academy in Madison, Wisconsin. Explore basketball training, skill camps, and competitive teams with Coach Will Turner.",
};

export default function Page() {
  return (
    <>
      <main id="main">
        <section className="page-hero">
          <p className="eyebrow">
            TRAINING &amp; CAMPS / P2V BASKETBALL ACADEMY
          </p>
          <h1>
            PUT IN
            <br />
            <em>THE WORK.</em>
          </h1>
          <p className="intro">
            Develop your basketball skills, build strength and speed, and learn
            to approach each session with purpose.
          </p>
        </section>
        <section className="section cream" id="skills">
          <div className="section-head">
            <div>
              <p className="eyebrow">PLAYER DEVELOPMENT</p>
              <h2>
                A stronger game.
                <br />A stronger athlete.
              </h2>
            </div>
            <p>
              Will and Tre Turner bring basketball training, strength, speed,
              and character development together.
            </p>
          </div>
          <TrainingTabs />
        </section>
        <section className="section equipment detail-backdrop">
          <div>
            <p className="eyebrow">TOOLS THAT SUPPORT THE WORK</p>
            <h2>
              Purposeful training.
              <br />
              Modern equipment.
            </h2>
            <p>
              P2V combines hands-on coaching with tools for shooting practice,
              reaction work, strength, and speed.
            </p>
            <a className="textlink" href="/facility.html">
              Explore the facility
            </a>
          </div>
          <div className="equipment-list">
            <div>
              <span>01</span>
              <h3>Dr. Dish + shot tracking</h3>
            </div>
            <div>
              <span>02</span>
              <h3>VertiMax &amp; Raptor</h3>
            </div>
            <div>
              <span>03</span>
              <h3>BlazePods</h3>
            </div>
          </div>
        </section>
        <section className="section cream" id="camps">
          <p className="eyebrow">SKILL CAMPS</p>
          <h2>
            Get in the gym.
            <br />
            Get after it.
          </h2>
          <div className="split-text">
            <p>
              Put focused time into your game in a camp setting. Ask the coaches
              about upcoming dates, age groups, pricing, and availability.
            </p>
            <a className="button dark" href="/contact.html?interest=Camps">
              Ask about camps
            </a>
          </div>
        </section>
        <CallToAction />
      </main>
      <SiteFooter />
    </>
  );
}
