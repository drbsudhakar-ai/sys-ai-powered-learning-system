import Image from "next/image";
import Link from "next/link";
import { useRef, useState } from "react";
import {
  AcademicCapIcon,
  ArrowPathIcon,
  ArrowRightIcon,
  Bars3Icon,
  BookOpenIcon,
  BuildingLibraryIcon,
  BuildingOffice2Icon,
  ChartBarSquareIcon,
  ChatBubbleLeftRightIcon,
  CheckIcon,
  ChevronDownIcon,
  ClipboardDocumentCheckIcon,
  ComputerDesktopIcon,
  HeartIcon,
  LifebuoyIcon,
  LightBulbIcon,
  MapIcon,
  PencilSquareIcon,
  PresentationChartLineIcon,
  QuestionMarkCircleIcon,
  ShieldCheckIcon,
  SparklesIcon,
  StarIcon,
  UserGroupIcon,
  UserIcon,
  WrenchScrewdriverIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

import styles from "./LandingPage.module.css";

const BRAND_ROOT = "/branding/sys-v2";

const navigation = [
  { label: "Mission", href: "#mission" },
  { label: "Programmes", href: "#programmes" },
  { label: "How SYS Works", href: "#how-sys-works" },
  { label: "Capabilities", href: "#capabilities" },
];

const programmes = [
  {
    id: "higher-education-entrance",
    title: "Higher Education Entrance",
    summary:
      "Preparation for JEE, NEET, CUET, PGCET, LAWCET, ICET, GATE and other entrance examinations.",
    details: [
      "Concept learning, guided revision and exam-aligned practice",
      "Topic-level assessments and performance evidence",
      "Targeted remediation for identified learning gaps",
    ],
    Icon: AcademicCapIcon,
  },
  {
    id: "employment-competitive-exams",
    title: "Employment & Competitive Exams",
    summary:
      "Preparation for SSC, Banking, Telangana State Government and other recruitment examinations.",
    details: [
      "Structured coverage across subjects and exam areas",
      "Question practice connected to topic performance",
      "Learning recommendations based on assessment evidence",
    ],
    Icon: BuildingLibraryIcon,
  },
  {
    id: "english-communication",
    title: "English Communication",
    summary:
      "Practical English and communication development for academic life, interviews and professional settings.",
    details: [
      "Guided speaking, writing and comprehension practice",
      "Progressive activities for practical communication",
      "Feedback that supports clarity and confidence",
    ],
    Icon: ChatBubbleLeftRightIcon,
  },
  {
    id: "motivation-student-support",
    title: "Motivation & Student Support",
    summary:
      "Personalized motivation, counselling, encouragement and learning guidance throughout the student journey.",
    details: [
      "Support connected to the learner’s current context",
      "Encouragement during difficult or interrupted progress",
      "Timely visibility for appropriate academic support",
    ],
    Icon: HeartIcon,
  },
];

const workflowSteps = [
  {
    id: "choose",
    number: "01",
    title: "Choose a goal",
    short: "Select a programme, subject or topic.",
    detail:
      "Students begin with the goal that matters to them. SYS preserves that choice while keeping the wider learning context connected.",
    points: ["Programme and subject choice", "Topic-level starting points"],
    Icon: MapIcon,
  },
  {
    id: "learn",
    number: "02",
    title: "Learn with guidance",
    short: "Build understanding in a structured session.",
    detail:
      "The AI Lecturer supports topic-aware learning while SYS can recommend prerequisites and a sensible sequence without removing student control.",
    points: ["Structured explanations", "Prerequisite recommendations"],
    Icon: BookOpenIcon,
  },
  {
    id: "practice",
    number: "03",
    title: "Practise & assess",
    short: "Turn learning into observable evidence.",
    detail:
      "Practice and assessments connect questions to subjects and topics so outcomes can inform the next learning action.",
    points: ["Topic-aware question practice", "Assessment evidence"],
    Icon: PencilSquareIcon,
  },
  {
    id: "understand",
    number: "04",
    title: "Understand performance",
    short: "See strengths, gaps and progress clearly.",
    detail:
      "Performance analysis brings learning and assessment evidence together to show where progress is strong and where attention is needed.",
    points: ["Subject and topic analysis", "Gap visibility"],
    Icon: ChartBarSquareIcon,
  },
  {
    id: "improve",
    number: "05",
    title: "Improve & master",
    short: "Act on gaps, reassess and continue.",
    detail:
      "SYS connects remedial learning, reassessment and mastery evidence into the ongoing learning journey rather than treating them as separate activities.",
    points: ["Targeted remedial learning", "Reassessment and mastery"],
    Icon: ArrowPathIcon,
  },
];

const capabilities = [
  {
    id: "ai-lecturer",
    title: "AI Lecturer",
    summary: "Structured, topic-aware digital learning sessions.",
    detail:
      "Supports explanations, learning sequences and guided classroom-style sessions while keeping the student’s selected subject and topic in view.",
    Icon: ComputerDesktopIcon,
  },
  {
    id: "question-intelligence",
    title: "Question Intelligence",
    summary: "Questions connected to learning context and evidence.",
    detail:
      "Organizes practice around subjects and topics so question history and outcomes can support assessment and future recommendations.",
    Icon: QuestionMarkCircleIcon,
  },
  {
    id: "assessments",
    title: "Assessments",
    summary: "A clear path from attempt to evaluated outcome.",
    detail:
      "Supports assessment creation, student attempts, evaluation and results as part of the same learning journey.",
    Icon: ClipboardDocumentCheckIcon,
  },
  {
    id: "performance-analysis",
    title: "Performance Analysis",
    summary: "Evidence interpreted at meaningful learning levels.",
    detail:
      "Connects results to course, subject and topic performance so students and academic teams can identify useful next actions.",
    Icon: PresentationChartLineIcon,
  },
  {
    id: "remedial-learning",
    title: "Remedial Learning",
    summary: "Focused support for specific learning gaps.",
    detail:
      "Turns identified gaps into targeted learning actions and prepares students to return to assessment with stronger understanding.",
    Icon: WrenchScrewdriverIcon,
  },
  {
    id: "mastery",
    title: "Mastery",
    summary: "Progress supported by evidence, not completion alone.",
    detail:
      "Tracks learning and reassessment evidence so mastery can develop over time rather than being inferred from a single activity.",
    Icon: StarIcon,
  },
  {
    id: "learning-journey",
    title: "Learning Journey",
    summary: "Context preserved across subjects, topics and returns.",
    detail:
      "Keeps progress and recommended next actions connected even when students switch subjects or revisit earlier learning.",
    Icon: MapIcon,
  },
  {
    id: "student-support",
    title: "Student Support",
    summary: "Motivation and guidance aligned with learning progress.",
    detail:
      "Connects encouragement and appropriate academic support to the learner’s current context, progress and persistent concerns.",
    Icon: LifebuoyIcon,
  },
];

const roles = [
  {
    id: "student",
    title: "Student",
    intro: "Choose, learn, practise and understand what comes next.",
    points: [
      "Move between programmes, subjects and topics",
      "Use learning, practice, assessments and remediation",
      "Review progress, gaps, mastery and journey guidance",
    ],
    Icon: UserIcon,
  },
  {
    id: "faculty",
    title: "Faculty",
    intro: "Use learning evidence to provide focused academic support.",
    points: [
      "Work with courses, questions and assessments",
      "Review student and topic-level performance evidence",
      "Identify where timely teaching support is needed",
    ],
    Icon: UserGroupIcon,
  },
  {
    id: "administrator",
    title: "Administrator",
    intro: "Coordinate the people and foundations behind the platform.",
    points: [
      "Manage students, faculty and core platform settings",
      "Maintain course and programme foundations",
      "Review operational and learning intelligence views",
    ],
    Icon: BuildingOffice2Icon,
  },
];

const faqs = [
  {
    id: "faq-login",
    question: "How do students, faculty and administrators sign in?",
    answer:
      "Everyone uses the same Login page. Access inside SYS follows the role and permissions associated with the authenticated account.",
  },
  {
    id: "faq-path",
    question: "Does SYS force every student through one fixed learning path?",
    answer:
      "No. Students may choose programmes, subjects and topics. SYS can recommend prerequisites, preserve context and highlight gaps while leaving the learning choice with the student.",
  },
  {
    id: "faq-programmes",
    question: "Which programme areas does SYS support?",
    answer:
      "The current programme structure covers higher-education entrance preparation, employment and competitive examinations, English communication, and motivation and student support.",
  },
  {
    id: "faq-faculty",
    question: "Does the AI Lecturer replace faculty?",
    answer:
      "No. SYS is designed to support learning and make evidence easier to act on. Faculty remain essential for teaching, judgment, intervention and student support.",
  },
  {
    id: "faq-progress",
    question: "How does SYS understand progress?",
    answer:
      "SYS connects learning activity, question practice, assessment outcomes, remedial work, reassessment and mastery evidence across the student’s learning journey.",
  },
];

function toggleSet(setter, id) {
  setter((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
}

function Brand({ footer = false }) {
  return (
    <Link href="/" className={styles.brand} aria-label="SYS — Strengthen Your Skills home">
      <Image
        src={`${BRAND_ROOT}/logos/SYS_Header_Logo_Dark.png`}
        alt="SYS — Strengthen Your Skills, AI-Powered Learning Platform"
        width={1200}
        height={280}
        priority={!footer}
        sizes={footer ? "(max-width: 680px) 285px, 295px" : "(max-width: 720px) 54px, 310px"}
        className={styles.brandDesktop}
      />
      <Image
        src={`${BRAND_ROOT}/logos/SYS_Symbol_Compact_Transparent.png`}
        alt=""
        width={900}
        height={872}
        priority={!footer}
        sizes="54px"
        className={styles.brandMobile}
      />
      <span className={styles.srOnly}>SYS — Strengthen Your Skills</span>
    </Link>
  );
}

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <Brand />
        <nav className={styles.desktopNav} aria-label="Primary navigation">
          {navigation.map((item) => (
            <a key={item.href} href={item.href} className={styles.navLink}>
              {item.label}
            </a>
          ))}
          <Link href="/login" className={styles.loginButton}>Login</Link>
        </nav>
        <button
          type="button"
          className={styles.menuButton}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          aria-controls="homepage-mobile-nav"
          onClick={() => setMenuOpen((value) => !value)}
        >
          {menuOpen ? <XMarkIcon /> : <Bars3Icon />}
        </button>
      </div>
      {menuOpen && (
        <nav id="homepage-mobile-nav" className={styles.mobileNav} aria-label="Mobile navigation">
          {navigation.map((item) => (
            <a key={item.href} href={item.href} onClick={closeMenu}>{item.label}</a>
          ))}
          <Link href="/login" className={styles.mobileLogin} onClick={closeMenu}>Login</Link>
        </nav>
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className={styles.hero} aria-labelledby="homepage-title">
      <div className={styles.heroInner}>
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}><SparklesIcon /> AI-Powered Learning Platform</p>
          <h1 id="homepage-title">One learning journey.<br /><span>Clearer next steps.</span></h1>
          <p className={styles.heroLead}>
            SYS connects learning, practice, assessment, performance analysis and targeted support so students and educators can act on the right next step.
          </p>
          <div className={styles.heroActions}>
            <Link href="/login" className={styles.primaryButton}>Login to SYS <ArrowRightIcon /></Link>
            <a href="#programmes" className={styles.secondaryButton}>Explore programmes</a>
          </div>
          <p className={styles.roleAccess}><ShieldCheckIcon /> One Login for Student, Faculty and Administrator access.</p>
        </div>
        <div className={styles.heroIdentity}>
          <div className={styles.identityCard}>
            <Image
              src={`${BRAND_ROOT}/logos/SYS_Master_Lockup_Transparent.png`}
              alt="SYS — Strengthen Your Skills. Shape Your Successful Future."
              width={900}
              height={650}
              priority
              sizes="(max-width: 820px) 86vw, 510px"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function Mission() {
  const pillars = [
    { title: "Choice with structure", text: "Students choose what to learn while SYS recommends helpful prerequisites and next actions.", Icon: MapIcon },
    { title: "Evidence into action", text: "Learning and assessment evidence becomes focused guidance, remediation and reassessment.", Icon: PresentationChartLineIcon },
    { title: "People stay in control", text: "AI supports learning decisions; students, faculty and administrators retain responsibility and judgment.", Icon: LightBulbIcon },
  ];

  return (
    <section id="mission" className={styles.missionSection} aria-labelledby="mission-title">
      <div className={styles.sectionInner}>
        <div className={styles.missionGrid}>
          <div>
            <p className={styles.sectionKicker}>Our mission</p>
            <h2 id="mission-title">Make every learning signal useful.</h2>
          </div>
          <p className={styles.missionStatement}>
            SYS is designed to bring teaching, practice, assessment and intervention into one continuous journey—so learners can progress with context and academic teams can support them with better evidence.
          </p>
        </div>
        <div className={styles.pillarGrid}>
          {pillars.map(({ title, text, Icon }) => (
            <article key={title} className={styles.pillarCard}>
              <span><Icon /></span><div><h3>{title}</h3><p>{text}</p></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Programmes() {
  const [openItems, setOpenItems] = useState(() => new Set());

  return (
    <section id="programmes" className={styles.programmeSection} aria-labelledby="programmes-title">
      <div className={styles.sectionInner}>
        <div className={styles.sectionHeading}>
          <p className={styles.sectionKicker}>Programme pathways</p>
          <h2 id="programmes-title">Different goals. One connected platform.</h2>
          <p>Explore the current SYS programme structure. Expand a card to see how learning support is organized.</p>
        </div>
        <div className={styles.programmeGrid}>
          {programmes.map(({ id, title, summary, details, Icon }) => {
            const open = openItems.has(id);
            return (
              <article key={id} className={`${styles.programmeCard} ${open ? styles.cardOpen : ""}`}>
                <button type="button" aria-expanded={open} aria-controls={`${id}-panel`} onClick={() => toggleSet(setOpenItems, id)}>
                  <span className={styles.cardIcon}><Icon /></span>
                  <span className={styles.cardHeading}><strong>{title}</strong><small>{summary}</small></span>
                  <ChevronDownIcon className={styles.chevron} />
                </button>
                <div id={`${id}-panel`} className={styles.expandPanel} hidden={!open}>
                  <ul>{details.map((detail) => <li key={detail}><CheckIcon />{detail}</li>)}</ul>
                  <Link href="/programs">View programmes <ArrowRightIcon /></Link>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function HowSysWorks() {
  const [activeIndex, setActiveIndex] = useState(0);
  const tabRefs = useRef([]);
  const active = workflowSteps[activeIndex];
  const ActiveIcon = active.Icon;

  const moveFocus = (event, index) => {
    let nextIndex = index;
    if (["ArrowRight", "ArrowDown"].includes(event.key)) nextIndex = (index + 1) % workflowSteps.length;
    else if (["ArrowLeft", "ArrowUp"].includes(event.key)) nextIndex = (index - 1 + workflowSteps.length) % workflowSteps.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = workflowSteps.length - 1;
    else return;
    event.preventDefault();
    setActiveIndex(nextIndex);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <section id="how-sys-works" className={styles.workflowSection} aria-labelledby="workflow-title">
      <div className={styles.sectionInner}>
        <div className={styles.sectionHeadingLight}>
          <p className={styles.sectionKicker}>How SYS works</p>
          <h2 id="workflow-title">From choice to mastery, every step stays connected.</h2>
          <p>Select a step to understand how the learning journey moves forward.</p>
        </div>
        <div className={styles.stepperShell}>
          <div className={styles.stepTabs} role="tablist" aria-label="SYS learning journey steps">
            {workflowSteps.map((step, index) => {
              const StepIcon = step.Icon;
              const selected = activeIndex === index;
              return (
                <button
                  key={step.id}
                  ref={(node) => { tabRefs.current[index] = node; }}
                  id={`${step.id}-tab`}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls={`${step.id}-tabpanel`}
                  tabIndex={selected ? 0 : -1}
                  className={selected ? styles.stepActive : ""}
                  onClick={() => setActiveIndex(index)}
                  onKeyDown={(event) => moveFocus(event, index)}
                >
                  <span className={styles.stepNumber}>{step.number}</span>
                  <span className={styles.stepIcon}><StepIcon /></span>
                  <span>{step.title}</span>
                </button>
              );
            })}
          </div>
          <div id={`${active.id}-tabpanel`} role="tabpanel" aria-labelledby={`${active.id}-tab`} className={styles.stepPanel}>
            <span className={styles.panelIcon}><ActiveIcon /></span>
            <div>
              <p className={styles.panelNumber}>Step {active.number}</p>
              <h3>{active.title}</h3>
              <p>{active.detail}</p>
              <ul>{active.points.map((point) => <li key={point}><CheckIcon />{point}</li>)}</ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Capabilities() {
  const [openItems, setOpenItems] = useState(() => new Set());

  return (
    <section id="capabilities" className={styles.capabilitySection} aria-labelledby="capabilities-title">
      <div className={styles.sectionInner}>
        <div className={styles.sectionHeading}>
          <p className={styles.sectionKicker}>Connected capabilities</p>
          <h2 id="capabilities-title">The learning system behind the journey.</h2>
          <p>Expand each capability to see the role it plays in SYS.</p>
        </div>
        <div className={styles.capabilityGrid}>
          {capabilities.map(({ id, title, summary, detail, Icon }) => {
            const open = openItems.has(id);
            return (
              <article key={id} className={`${styles.capabilityCard} ${open ? styles.cardOpen : ""}`}>
                <button type="button" aria-expanded={open} aria-controls={`${id}-detail`} onClick={() => toggleSet(setOpenItems, id)}>
                  <span className={styles.capabilityIcon}><Icon /></span>
                  <span><strong>{title}</strong><small>{summary}</small></span>
                  <ChevronDownIcon className={styles.chevron} />
                </button>
                <p id={`${id}-detail`} className={styles.capabilityDetail} hidden={!open}>{detail}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Roles() {
  const [openItems, setOpenItems] = useState(() => new Set());

  return (
    <section className={styles.rolesSection} aria-labelledby="roles-title">
      <div className={styles.sectionInner}>
        <div className={styles.sectionHeading}>
          <p className={styles.sectionKicker}>One platform, role-aware access</p>
          <h2 id="roles-title">Built for the people who shape learning.</h2>
          <p>Student, Faculty and Administrator accounts use the same Login page and enter the experience appropriate to their role.</p>
        </div>
        <div className={styles.roleGrid}>
          {roles.map(({ id, title, intro, points, Icon }) => {
            const open = openItems.has(id);
            return (
              <article key={id} className={`${styles.roleCard} ${open ? styles.cardOpen : ""}`}>
                <button type="button" aria-expanded={open} aria-controls={`${id}-role-detail`} onClick={() => toggleSet(setOpenItems, id)}>
                  <span className={styles.roleIcon}><Icon /></span>
                  <span><strong>{title}</strong><small>{intro}</small></span>
                  <ChevronDownIcon className={styles.chevron} />
                </button>
                <div id={`${id}-role-detail`} className={styles.roleDetail} hidden={!open}>
                  <ul>{points.map((point) => <li key={point}><CheckIcon />{point}</li>)}</ul>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Faq() {
  const [openId, setOpenId] = useState(null);

  return (
    <section id="faq" className={styles.faqSection} aria-labelledby="faq-title">
      <div className={styles.faqInner}>
        <div className={styles.faqIntro}>
          <p className={styles.sectionKicker}>Frequently asked questions</p>
          <h2 id="faq-title">A clear starting point.</h2>
          <p>Practical answers about access, learning choice and how SYS supports academic work.</p>
        </div>
        <div className={styles.faqList}>
          {faqs.map(({ id, question, answer }) => {
            const open = openId === id;
            return (
              <article key={id} className={open ? styles.faqOpen : ""}>
                <button type="button" aria-expanded={open} aria-controls={`${id}-answer`} onClick={() => setOpenId(open ? null : id)}>
                  <span>{question}</span><ChevronDownIcon />
                </button>
                <p id={`${id}-answer`} hidden={!open}>{answer}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function LoginCta() {
  return (
    <section className={styles.ctaSection} aria-labelledby="cta-title">
      <div className={styles.ctaInner}>
        <div><p className={styles.sectionKicker}>Continue your SYS journey</p><h2 id="cta-title">One Login. The right workspace for your role.</h2><p>Access Student, Faculty or Administrator features using your existing SYS account.</p></div>
        <Link href="/login" className={styles.ctaButton}>Login to SYS <ArrowRightIcon /></Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        <div className={styles.footerBrand}><Brand footer /><p>AI-powered learning, assessment and student support in one connected journey.</p></div>
        <div className={styles.footerNavGroup}>
          <nav aria-label="Homepage sections"><h2>Explore</h2><a href="#mission">Mission</a><a href="#programmes">Programmes</a><a href="#how-sys-works">How SYS Works</a><a href="#capabilities">Capabilities</a><a href="#faq">FAQ</a></nav>
          <nav aria-label="Platform links"><h2>Platform</h2><Link href="/programs">Programs page</Link><Link href="/login">Login</Link></nav>
        </div>
      </div>
      <div className={styles.footerBottom}><span>© {new Date().getFullYear()} SYS — Strengthen Your Skills.</span><span>Shape Your Successful Future.</span></div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className={styles.page}>
      <Header />
      <main>
        <Hero />
        <Mission />
        <Programmes />
        <HowSysWorks />
        <Capabilities />
        <Roles />
        <Faq />
        <LoginCta />
      </main>
      <Footer />
    </div>
  );
}
