import Image from "next/image";

import ExamPrepIllustration from "../components/features/ExamPrepIllustration";
import EntranceCoachingIllustration from "../components/features/EntranceCoachingIllustration";
import CommunicationIllustration from "../components/features/CommunicationIllustration";
import AICounsellorIllustration from "../components/features/AICounsellorIllustration";


const features = [
  {
    title: "Competitive Exams Coaching",
    slug: "competitive-exams",
    description:
      "AI-tailored resources and practice designed to help you perform better in competitive examinations.",
    Illustration: ExamPrepIllustration,
  },
  {
    title: "Entrance Test Coaching",
    slug: "entrance-tests",
    description:
      "Structured preparation and guided practice for higher-education entrance examinations.",
    Illustration: EntranceCoachingIllustration,
  },
  {
    title: "Communication Skills",
    slug: "communication-skills",
    description:
      "Improve speaking, writing, confidence and communication through guided AI-powered practice.",
    Illustration: CommunicationIllustration,
  },
  {
    title: "AI Counsellor",
    slug: "ai-counsellor",
    description:
      "Personalized guidance, motivation and encouragement tailored to your learning journey.",
    Illustration: AICounsellorIllustration,
  },
];
export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#120a2d] text-white">
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-[520px] w-[520px] rounded-full bg-violet-500/20 blur-[130px]" />
        <div className="absolute right-[-180px] top-[80px] h-[520px] w-[520px] rounded-full bg-indigo-500/20 blur-[140px]" />
        <div className="absolute bottom-[-220px] left-[30%] h-[560px] w-[560px] rounded-full bg-fuchsia-500/15 blur-[150px]" />

        <div
          className="absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.55) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.55) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
      </div>

      {/* HERO */}
      <section className="relative mx-auto max-w-7xl px-5 pb-20 pt-14 sm:px-6 lg:px-8 lg:pb-28 lg:pt-20">
        <div className="grid items-center gap-14 lg:grid-cols-[1.05fr_.95fr] lg:gap-8">
          <div className="text-center lg:text-left">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm font-medium text-purple-100/80 shadow-lg shadow-purple-950/10 backdrop-blur-md">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              AI-Powered Learning Platform
            </div>

            <h1 className="text-5xl font-black leading-[1.02] tracking-[-0.04em] sm:text-6xl lg:text-[76px]">
              <span className="block">Strengthen Your</span>
              <span className="mt-2 block bg-gradient-to-r from-indigo-300 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                Skills.
              </span>
              <span className="mt-2 block">Shape Your Future.</span>
            </h1>

            <p className="mx-auto mt-7 max-w-2xl text-base leading-7 text-purple-100/65 sm:text-lg lg:mx-0">
              Your smart learning companion for personalized exam preparation,
              communication training and AI-powered skill development.
            </p>

            <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row lg:justify-start">
              <a
                href="#programs"
                className="rounded-xl bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 px-7 py-3.5 text-center font-bold shadow-xl shadow-violet-900/30 transition duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-violet-700/30"
              >
                Start Learning
              </a>

              <a
                href="#programs"
                className="rounded-xl border border-white/15 bg-white/[0.05] px-7 py-3.5 text-center font-bold text-white backdrop-blur-md transition duration-300 hover:-translate-y-1 hover:bg-white/[0.10]"
              >
                Explore Programs
              </a>
            </div>

            <div className="mt-9 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm text-purple-100/55 lg:justify-start">
              <span>✓ Personalized Learning</span>
              <span>✓ AI Powered</span>
              <span>✓ Skill Focused</span>
            </div>
          </div>

          {/* Hero visual */}
{/* ============================================================
    HERO LOGO / AI VISUAL
    Uses the exact full-resolution SYS logo
============================================================ */}

    <div className="relative flex min-h-[520px] items-center justify-center lg:min-h-[600px]">

      {/* Ambient glow */}
      <div className="
        pointer-events-none
        absolute
        h-[430px]
        w-[430px]
        rounded-full
        bg-violet-600/30
        blur-[120px]
      " />

      <div className="
        pointer-events-none
        absolute
        right-[5%]
        top-[15%]
        h-[280px]
        w-[280px]
        rounded-full
        bg-fuchsia-500/20
        blur-[110px]
      " />

      {/* ==========================================================
          MAIN ORB
      =========================================================== */}

      <div className="
        relative
        z-10
        flex
        h-[390px]
        w-[390px]
        items-center
        justify-center
        rounded-full
        p-[8px]
        bg-gradient-to-br
        from-cyan-400
        via-violet-500
        to-fuchsia-500
        shadow-[0_0_60px_rgba(139,92,246,0.55)]
        sm:h-[450px]
        sm:w-[450px]
        lg:h-[480px]
        lg:w-[480px]
      ">

        {/* Outer glass ring */}
        <div className="
          relative
          flex
          h-full
          w-full
          items-center
          justify-center
          overflow-hidden
          rounded-full
          border
          border-white/30
          bg-[#08052c]/75
          shadow-[inset_0_0_60px_rgba(99,102,241,0.22)]
          backdrop-blur-xl
        ">

          {/* Inner ring */}
          <div className="
            pointer-events-none
            absolute
            inset-[22px]
            rounded-full
            border
            border-white/20
          " />

          {/* Inner violet glow */}
          <div className="
            pointer-events-none
            absolute
            inset-[45px]
            rounded-full
            bg-gradient-to-br
            from-indigo-500/10
            via-violet-500/15
            to-fuchsia-500/10
            blur-2xl
          " />

          {/* ======================================================
              EXACT SYS LOGO
          ======================================================= */}

          <div className="
            relative
            z-20
            flex
            h-[270px]
            w-[270px]
            items-center
            justify-center
            sm:h-[315px]
            sm:w-[315px]
            lg:h-[350px]
            lg:w-[350px]
          ">

            <Image
              src="/sys-logo.png"
              alt="SYS – Strengthen Your Skills"
              width={500}
              height={500}
              priority
              unoptimized
              sizes="350px"
              className="
                h-full
                w-full
                object-contain
                drop-shadow-[0_15px_35px_rgba(0,0,0,0.55)]
              "
            />

          </div>

        </div>
      </div>

      {/* ==========================================================
          FLOATING POWERED BY CARD
      =========================================================== */}

      <div className="
        absolute
        right-0
        top-[70px]
        z-30
        rounded-2xl
        border
        border-white/15
        bg-white/[0.08]
        px-5
        py-3
        shadow-xl
        backdrop-blur-xl
        sm:right-[5px]
      ">
        <div className="text-[11px] text-purple-200/60">
          Powered by
        </div>

        <div className="font-bold text-white">
          AI Learning
        </div>
      </div>

      {/* ==========================================================
          LEARNING PROGRESS
      =========================================================== */}

      <div className="
        absolute
        bottom-[70px]
        left-0
        z-30
        rounded-2xl
        border
        border-white/15
        bg-white/[0.08]
        px-5
        py-3
        shadow-xl
        backdrop-blur-xl
        sm:left-[5px]
      ">
        <div className="text-[11px] text-purple-200/60">
          Learning Progress
        </div>

        <div className="font-bold text-emerald-400">
          +87%
        </div>
      </div>

      {/* ==========================================================
          HOLOGRAPHIC PLATFORM
      =========================================================== */}

      <div className="
        pointer-events-none
        absolute
        bottom-[35px]
        left-1/2
        z-20
        h-[75px]
        w-[390px]
        -translate-x-1/2
        rounded-[50%]
        border
        border-violet-300/70
        bg-gradient-to-r
        from-indigo-500/20
        via-violet-400/30
        to-fuchsia-500/20
        shadow-[0_0_35px_rgba(139,92,246,0.75)]
        sm:w-[460px]
        lg:w-[500px]
      ">

        <div className="
          absolute
          inset-[10px]
          rounded-[50%]
          border
          border-white/30
        " />

        <div className="
          absolute
          left-1/2
          top-1/2
          h-3
          w-[65%]
          -translate-x-1/2
          -translate-y-1/2
          rounded-full
          bg-gradient-to-r
          from-cyan-400
          via-violet-400
          to-fuchsia-400
          blur-md
        " />

      </div>

    </div>
        </div>
      </section>

      {/* PROGRAMS */}

      <section id="programs" className="relative mx-auto max-w-7xl px-5 pb-24 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <div className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-violet-300">
            What We Offer
          </div>

          <h2 className="text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
            Explore Our{" "}
            <span className="bg-gradient-to-r from-indigo-300 to-fuchsia-400 bg-clip-text text-transparent">
              Programs
            </span>
          </h2>

          <p className="mt-4 text-purple-100/60">
            Choose a program to see its complete features, learning path and
            detailed information.
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ title, slug, description, Illustration }) => (
            <a
              key={title}
              href={`/programs#${slug}`}
              className="group relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.055] p-6 shadow-xl shadow-black/10 backdrop-blur-xl transition-all duration-500 hover:-translate-y-2 hover:border-violet-300/30 hover:bg-white/[0.09] hover:shadow-2xl hover:shadow-violet-950/30 focus:outline-none focus:ring-2 focus:ring-violet-400/70"
              aria-label={`View ${title} program`}
            >
              <div className="absolute -right-16 -top-16 h-36 w-36 rounded-full bg-violet-500/10 blur-3xl transition duration-500 group-hover:bg-fuchsia-500/20" />

              <div className="relative mb-6 flex h-36 items-center justify-center">
                <div className="absolute h-28 w-28 rounded-full bg-white/[0.04] blur-2xl" />
                <Illustration
                  size={130}
                  className="relative z-10 transition duration-500 group-hover:scale-110 group-hover:-rotate-2"
                />
              </div>

              <h3 className="text-xl font-bold leading-tight">{title}</h3>

              <p className="mt-3 min-h-[96px] text-sm leading-6 text-purple-100/58">
                {description}
              </p>

              <div className="mt-5 flex items-center gap-2 text-sm font-semibold text-violet-300 transition-all duration-300 group-hover:gap-3 group-hover:text-white">
                View program <span>→</span>
              </div>
            </a>
          ))}
        </div>

        <div className="mt-10 text-center">
          <a
            href="/programs"
            className="inline-flex rounded-xl border border-violet-400/30 bg-violet-500/10 px-6 py-3 font-semibold text-violet-200 transition hover:bg-violet-500/20 hover:text-white"
          >
            View All Programs →
          </a>
        </div>
      </section>





      {/* <section id="programs" className="relative mx-auto max-w-7xl px-5 pb-24 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <div className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-violet-300">
            What We Offer
          </div>

          <h2 className="text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
            Explore Our{" "}
            <span className="bg-gradient-to-r from-indigo-300 to-fuchsia-400 bg-clip-text text-transparent">
              Programs
            </span>
          </h2>

          <p className="mt-4 text-purple-100/60">
            Everything you need to prepare, improve your skills and build
            confidence with personalized AI guidance.
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ title, description, Illustration }) => (
            <article
              key={title}
              className="group relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.055] p-6 shadow-xl shadow-black/10 backdrop-blur-xl transition-all duration-500 hover:-translate-y-2 hover:border-violet-300/20 hover:bg-white/[0.09] hover:shadow-2xl hover:shadow-violet-950/30"
            >
              <div className="absolute -right-16 -top-16 h-36 w-36 rounded-full bg-violet-500/10 blur-3xl transition duration-500 group-hover:bg-fuchsia-500/20" />

              <div className="relative mb-6 flex h-36 items-center justify-center">
                <div className="absolute h-28 w-28 rounded-full bg-white/[0.04] blur-2xl" />
                <Illustration
                  size={130}
                  className="relative z-10 transition duration-500 group-hover:scale-110 group-hover:-rotate-2"
                />
              </div>

              <h3 className="text-xl font-bold leading-tight">{title}</h3>

              <p className="mt-3 min-h-[96px] text-sm leading-6 text-purple-100/58">
                {description}
              </p>

              <div className="mt-5 flex items-center gap-2 text-sm font-semibold text-violet-300 transition-all duration-300 group-hover:gap-3 group-hover:text-white">
                Learn more <span>→</span>
              </div>
            </article>
          ))}
        </div>
      </section> */}



      {/* <section id="programs" className="relative mx-auto max-w-7xl px-5 pb-24 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <div className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-violet-300">
            What We Offer
          </div>

          <h2 className="text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
            Explore Our{" "}
            <span className="bg-gradient-to-r from-indigo-300 to-fuchsia-400 bg-clip-text text-transparent">
              Programs
            </span>
          </h2>

          <p className="mt-4 text-purple-100/60">
            Everything you need to prepare, improve your skills and build
            confidence with personalized AI guidance.
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ title, description, Illustration }) => (
            <article
              key={title}
              className="group relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.055] p-6 shadow-xl shadow-black/10 backdrop-blur-xl transition-all duration-500 hover:-translate-y-2 hover:border-violet-300/20 hover:bg-white/[0.09] hover:shadow-2xl hover:shadow-violet-950/30"
            >
              <div className="absolute -right-16 -top-16 h-36 w-36 rounded-full bg-violet-500/10 blur-3xl transition duration-500 group-hover:bg-fuchsia-500/20" />

              <div className="relative mb-6 flex h-36 items-center justify-center">
                <div className="absolute h-28 w-28 rounded-full bg-white/[0.04] blur-2xl" />
                <Illustration
                  size={130}
                  className="relative z-10 transition duration-500 group-hover:scale-110 group-hover:-rotate-2"
                />
              </div>

              <h3 className="text-xl font-bold leading-tight">{title}</h3>

              <p className="mt-3 min-h-[96px] text-sm leading-6 text-purple-100/58">
                {description}
              </p>

              <div className="mt-5 flex items-center gap-2 text-sm font-semibold text-violet-300 transition-all duration-300 group-hover:gap-3 group-hover:text-white">
                Learn more <span>→</span>
              </div>
            </article>
          ))}
        </div>
      </section> */}

      {/* STATS */}
      <section className="relative border-y border-white/10 bg-white/[0.025]">
        <div className="mx-auto grid max-w-5xl grid-cols-2 divide-x divide-y divide-white/10 px-5 py-10 md:grid-cols-4 md:divide-y-0">
          {[
            ["4+", "Learning Programs"],
            ["AI", "Personalized"],
            ["24/7", "Learning Support"],
            ["∞", "Possibilities"],
          ].map(([value, label]) => (
            <div key={label} className="px-4 py-4 text-center">
              <div className="text-3xl font-black sm:text-4xl">{value}</div>
              <div className="mt-1 text-sm text-purple-200/50">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative mx-auto max-w-5xl px-5 py-20 sm:px-6 lg:py-24">
        <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-indigo-600/25 via-violet-600/20 to-fuchsia-600/20 px-6 py-14 text-center shadow-2xl shadow-violet-950/30 backdrop-blur-xl sm:px-12 sm:py-16">
          <div className="absolute left-1/2 top-0 h-40 w-80 -translate-x-1/2 rounded-full bg-violet-500/20 blur-[100px]" />

          <div className="relative">
            <div className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-violet-200">
              Your Future Starts Here
            </div>

            <h2 className="text-3xl font-black sm:text-4xl">
              Ready to Strengthen Your Skills?
            </h2>

            <p className="mx-auto mt-4 max-w-xl text-purple-100/60">
              Start your personalized learning journey and take the next step
              toward your academic and professional goals.
            </p>

            <a
              href="#programs"
              className="mt-8 inline-flex rounded-xl bg-white px-8 py-3.5 font-bold text-violet-950 shadow-xl transition duration-300 hover:-translate-y-1 hover:shadow-2xl"
            >
              Get Started →
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
