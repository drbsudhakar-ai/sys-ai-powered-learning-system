/**
 * Global SYS Header
 * Uses the exact full-resolution /public/sys-logo.png
 */

import Image from "next/image";
import Link from "next/link";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0b0624]/95 shadow-lg shadow-black/20 backdrop-blur-xl">
      <div className="mx-auto flex min-h-[88px] w-full max-w-7xl items-center px-4 sm:px-6 lg:px-8">

        {/* =====================================================
            SYS LOGO
            Exact full-resolution logo from public/sys-logo.png
        ====================================================== */}

        <Link
          href="/"
          aria-label="SYS – Strengthen Your Skills"
          className="group shrink-0"
        >
          <div
            className="
              relative
              flex
              h-[82px]
              w-[82px]
              items-center
              justify-center
              overflow-hidden
              rounded-full
              border-2
              border-fuchsia-400/80
              bg-[#10082e]
              shadow-[0_0_25px_rgba(168,85,247,0.55)]
              transition-all
              duration-300
              group-hover:scale-105
              group-hover:border-fuchsia-300
              group-hover:shadow-[0_0_35px_rgba(217,70,239,0.75)]
            "
          >
            <Image
              src="/sys-logo.png"
              alt="SYS – Strengthen Your Skills"
              width={82}
              height={82}
              priority
              unoptimized
              sizes="82px"
              className="
                h-full
                w-full
                object-contain
                p-[4px]
              "
            />

            {/* Inner circular border */}
            <div className="pointer-events-none absolute inset-[3px] rounded-full border border-white/20" />
          </div>
        </Link>

        {/* =====================================================
            BRAND NAME
        ====================================================== */}

        <Link
          href="/"
          className="ml-4 min-w-0"
        >
          <div className="truncate text-lg font-extrabold tracking-tight text-white sm:text-xl">
            SYS
            <span className="hidden sm:inline">
              {" "}– Strengthen Your Skills
            </span>
          </div>

          <div className="mt-1 text-[11px] font-medium tracking-wide text-purple-200/65 sm:text-xs">
            AI-Powered Learning Platform
          </div>
        </Link>

        {/* =====================================================
            NAVIGATION
        ====================================================== */}

        <nav
          className="ml-auto hidden items-center gap-1 lg:flex"
          aria-label="Main navigation"
        >
          <Link
            href="/"
            className="
              rounded-xl
              bg-violet-600/30
              px-5
              py-2.5
              text-sm
              font-bold
              text-white
              ring-1
              ring-violet-400/30
              transition
              hover:bg-violet-600/45
            "
          >
            Home
          </Link>

          <Link
          href="/programs"
          className="
            rounded-xl
            px-5
            py-2.5
            text-sm
            font-semibold
            text-purple-100/70
            transition
            hover:bg-white/10
            hover:text-white
          "
        >
          Programs
        </Link>

          <Link
            href="/courses"
            className="
              rounded-xl
              px-5
              py-2.5
              text-sm
              font-semibold
              text-purple-100/70
              transition
              hover:bg-white/10
              hover:text-white
            "
          >
            Courses
          </Link>

          <Link
            href="/question-bank"
            className="
              rounded-xl
              px-5
              py-2.5
              text-sm
              font-semibold
              text-purple-100/70
              transition
              hover:bg-white/10
              hover:text-white
            "
          >
            Question Bank
          </Link>

          <Link
            href="/assessments"
            className="
              rounded-xl
              px-5
              py-2.5
              text-sm
              font-semibold
              text-purple-100/70
              transition
              hover:bg-white/10
              hover:text-white
            "
          >
            Assessments
          </Link>

          <Link
            href="/admin-dashboard"
            className="
              rounded-xl
              px-5
              py-2.5
              text-sm
              font-semibold
              text-purple-100/70
              transition
              hover:bg-white/10
              hover:text-white
            "
          >
            Admin
          </Link>

          <a
            href="/#about"
            className="
              rounded-xl
              px-5
              py-2.5
              text-sm
              font-semibold
              text-purple-100/70
              transition
              hover:bg-white/10
              hover:text-white
            "
          >
            About Us
          </a>

          <a
            href="/#contact"
            className="
              rounded-xl
              px-5
              py-2.5
              text-sm
              font-semibold
              text-purple-100/70
              transition
              hover:bg-white/10
              hover:text-white
            "
          >
            Contact
          </a>

          {/* <span className="mx-4 h-7 w-px bg-white/15" />

          <Link
            href="/login"
            className="
              rounded-xl
              border
              border-white/25
              px-5
              py-2.5
              text-sm
              font-bold
              text-white
              transition
              hover:border-violet-300/60
              hover:bg-white/10
            "
          >
            Login
          </Link>

          <Link
            href="/signup"
            className="
              ml-2
              rounded-xl
              bg-gradient-to-r
              from-indigo-500
              via-violet-500
              to-fuchsia-500
              px-5
              py-2.5
              text-sm
              font-bold
              text-white
              shadow-lg
              shadow-violet-900/30
              transition
              hover:-translate-y-0.5
              hover:shadow-xl
            "
          >
            Sign Up
          </Link> */}
        </nav>

      </div>
    </header>
  );
}