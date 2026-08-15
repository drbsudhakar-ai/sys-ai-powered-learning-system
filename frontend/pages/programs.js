import Head from "next/head";
import Link from "next/link";

import ExamPrepIllustration from "../components/features/ExamPrepIllustration";
import EntranceCoachingIllustration from "../components/features/EntranceCoachingIllustration";
import CommunicationIllustration from "../components/features/CommunicationIllustration";
import AICounsellorIllustration from "../components/features/AICounsellorIllustration";

const programs = [
  {
    id: "competitive-exams",
    number: "01",
    title: "Competitive Exams Coaching",
    short:
      "AI-tailored preparation and practice designed to help learners perform better in competitive examinations.",
    description:
      "Build a focused preparation strategy with structured learning, practice, revision and AI-powered guidance tailored to your learning needs.",
    Illustration: ExamPrepIllustration,
    accent: "from-indigo-400 to-violet-500",
    features: [
      "Personalized exam preparation plan",
      "Topic-wise learning and practice",
      "Practice questions and mock tests",
      "Performance and progress tracking",
      "AI-powered explanations and learning support",
      "Revision-focused preparation",
    ],
  },
  {
    id: "entrance-tests",
    number: "02",
    title: "Entrance Test Coaching",
    short:
      "Structured preparation and guided practice for higher-education entrance examinations.",
    description:
      "Prepare systematically for entrance examinations with organized study resources, targeted practice and continuous performance feedback.",
    Illustration: EntranceCoachingIllustration,
    accent: "from-pink-400 to-fuchsia-500",
    features: [
      "Structured entrance-test preparation",
      "Subject and topic-wise practice",
      "Question-bank based learning",
      "Mock-test and assessment support",
      "Weak-area identification",
      "Personalized improvement guidance",
    ],
  },
  {
    id: "communication-skills",
    number: "03",
    title: "English Communication",
    short:
      "Improve speaking, writing, confidence and communication through guided AI-powered practice.",
    description:
      "Develop practical communication abilities through continuous practice, guided feedback and activities designed around real-world communication.",
    Illustration: CommunicationIllustration,
    accent: "from-emerald-400 to-cyan-500",
    features: [
      "Speaking practice and confidence building",
      "Writing and vocabulary development",
      "Grammar and sentence improvement",
      "Interactive communication exercises",
      "AI-guided feedback",
      "Progress-based skill development",
    ],
  },
  {
    id: "ai-counsellor",
    number: "04",
    title: "Motivation & Support",
    short:
      "Personalized guidance, motivation and encouragement tailored to the learner's journey.",
    description:
      "Get intelligent learning guidance and personalized support to help identify goals, choose learning priorities and stay motivated.",
    Illustration: AICounsellorIllustration,
    accent: "from-amber-400 to-orange-500",
    features: [
      "Personalized learning guidance",
      "Goal-setting assistance",
      "Study-planning support",
      "Learning-path recommendations",
      "Motivation and encouragement",
      "AI-powered learner assistance",
    ],
  },
];

export default function Programs() {
  return (
    <>
      <Head>
        <title>Programs | SYS – Strengthen Your Skills</title>
        <meta
          name="description"
          content="Explore SYS learning programs for competitive exams, entrance tests, communication skills and AI-powered counselling."
        />
      </Head>

      <main
        id="top"
        className="relative min-h-screen overflow-hidden bg-[#120a2d] text-white"
      >
        {/* Background */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-40 top-20 h-[500px] w-[500px] rounded-full bg-violet-600/15 blur-[140px]" />
          <div className="absolute right-[-180px] top-[500px] h-[600px] w-[600px] rounded-full bg-fuchsia-600/10 blur-[150px]" />

          <div
            className="absolute inset-0 opacity-[0.035]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.6) 1px, transparent 1px)",
              backgroundSize: "48px 48px",
            }}
          />
        </div>

        {/* Heading */}
        <section className="relative mx-auto max-w-7xl px-5 pb-10 pt-14 sm:px-6 lg:px-8 lg:pt-20">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-violet-400/20 bg-violet-500/[0.08] px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-violet-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              SYS Learning Programs
            </div>

            <h1 className="text-4xl font-black tracking-[-0.035em] sm:text-5xl lg:text-6xl">
              Learn. Practice.{" "}
              <span className="bg-gradient-to-r from-indigo-300 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                Improve.
              </span>
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-purple-100/60 sm:text-lg">
              Choose the learning program that matches your goal. SYS combines
              structured learning, practice and AI-powered guidance to help
              you strengthen your skills.
            </p>
          </div>
        </section>

        {/* Program quick navigation */}
        <section className="relative mx-auto max-w-7xl px-5 pb-12 sm:px-6 lg:px-8">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {programs.map(({ id, number, title, Illustration, accent }) => (
              <a
                key={id}
                href={`#${id}`}
                className="group rounded-2xl border border-white/10 bg-white/[0.045] p-5 backdrop-blur-xl transition hover:-translate-y-1 hover:border-violet-400/30 hover:bg-white/[0.08]"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black tracking-[0.2em] text-purple-300/60">
                    {number}
                  </span>
                  <div
                    className={`h-1.5 w-12 rounded-full bg-gradient-to-r ${accent}`}
                  />
                </div>

                <div className="mt-4 flex items-center gap-4">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-white/[0.06]">
                    <Illustration size={52} />
                  </div>
                  <h2 className="text-sm font-bold leading-5 text-white">
                    {title}
                  </h2>
                </div>
              </a>
            ))}
          </div>
        </section>

        {/* Detailed programs */}
        <section className="relative mx-auto max-w-7xl px-5 pb-24 sm:px-6 lg:px-8">
          <div className="space-y-7">
            {programs.map(
              ({
                id,
                number,
                title,
                short,
                description,
                Illustration,
                accent,
                features,
              }) => (
                <article
                  id={id}
                  key={id}
                  className="scroll-mt-28 overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.045] shadow-2xl shadow-black/10 backdrop-blur-xl"
                >
                  <div className="grid lg:grid-cols-[0.8fr_1.2fr]">
                    {/* Program illustration */}
                    <div className="relative flex min-h-[300px] items-center justify-center overflow-hidden p-8 lg:min-h-[390px]">
                      <div
                        className={`absolute h-72 w-72 rounded-full bg-gradient-to-br ${accent} opacity-15 blur-[80px]`}
                      />

                      <div className="relative flex h-64 w-64 items-center justify-center rounded-full border border-white/10 bg-[#19103b]/80 shadow-[0_0_70px_rgba(139,92,246,0.18)] sm:h-72 sm:w-72">
                        <div className="absolute inset-4 rounded-full border border-white/10" />
                        <Illustration size={190} className="relative z-10" />
                      </div>

                      <div className="absolute left-7 top-7 rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs font-black tracking-[0.2em] text-purple-200/60">
                        PROGRAM {number}
                      </div>
                    </div>

                    {/* Program details */}
                    <div className="border-t border-white/10 p-7 sm:p-9 lg:border-l lg:border-t-0 lg:p-12">
                      <div
                        className={`mb-3 inline-block bg-gradient-to-r ${accent} bg-clip-text text-xs font-black uppercase tracking-[0.25em] text-transparent`}
                      >
                        AI-Powered Learning
                      </div>

                      <h2 className="text-3xl font-black tracking-tight sm:text-4xl">
                        {title}
                      </h2>

                      <p className="mt-4 text-base font-medium leading-7 text-purple-100/75">
                        {short}
                      </p>

                      <p className="mt-3 max-w-2xl text-sm leading-6 text-purple-100/50">
                        {description}
                      </p>

                      <div className="mt-8">
                        <h3 className="text-sm font-bold uppercase tracking-[0.18em] text-white/80">
                          Salient Features
                        </h3>

                        <div className="mt-4 grid gap-3 sm:grid-cols-2">
                          {features.map((feature) => (
                            <div
                              key={feature}
                              className="flex items-start gap-3 rounded-xl border border-white/8 bg-black/10 px-4 py-3"
                            >
                              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-400/10 text-xs font-bold text-emerald-400">
                                ✓
                              </span>

                              <span className="text-sm leading-5 text-purple-100/70">
                                {feature}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="mt-8 flex flex-wrap gap-3">
                        <Link
                          href="/login"
                          className="rounded-xl bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 px-6 py-3 text-sm font-bold shadow-lg shadow-violet-900/20 transition hover:-translate-y-0.5"
                        >
                          Start Learning →
                        </Link>

                        <a
                          href="#top"
                          className="rounded-xl border border-white/15 px-6 py-3 text-sm font-semibold text-purple-100/70 transition hover:bg-white/10 hover:text-white"
                        >
                          Back to Programs
                        </a>
                      </div>
                    </div>
                  </div>
                </article>
              )
            )}
          </div>
        </section>

        {/* CTA */}
        <section className="relative mx-auto max-w-5xl px-5 pb-24 sm:px-6 lg:px-8">
          <div className="overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-indigo-600/20 via-violet-600/15 to-fuchsia-600/20 p-8 text-center shadow-2xl shadow-violet-950/20 sm:p-12">
            <div className="text-xs font-black uppercase tracking-[0.25em] text-violet-300">
              Start Your Journey
            </div>

            <h2 className="mt-3 text-3xl font-black sm:text-4xl">
              Choose Your Program and Start Learning
            </h2>

            <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-purple-100/55">
              Strengthen your academic preparation, communication abilities and
              learning confidence with SYS.
            </p>

            <Link
              href="/login"
              className="mt-7 inline-flex rounded-xl bg-white px-7 py-3.5 font-bold text-violet-950 transition hover:-translate-y-1"
            >
              Get Started →
            </Link>
          </div>
        </section>
      </main>
    </>
  );
}
