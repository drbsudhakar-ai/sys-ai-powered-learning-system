import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { clearSession, roleLandingPath } from "../../src/auth";

const QUICK_LINKS = [
  { label: "Home", href: "/" },
  { label: "Programs", href: "/programs" },
];

const PLATFORM_LINKS = [
  { label: "Explore programmes", href: "/programs" },
];

export default function SYSFooter({
  session = { status: "anonymous", user: null },
}) {
  const router = useRouter();

  const authenticated =
    session.status === "authenticated" && session.user;

  const dashboardPath = authenticated
    ? roleLandingPath(session.user.role) || "/dashboard"
    : null;

  const logout = () => {
    clearSession();
    router.push("/login?reason=signed-out");
  };

  return (
    <footer className="sys-footer">
      <div className="sys-footer-main">
        {/* Brand */}
        <div className="sys-footer-brand">
          <Link
            href="/"
            className="sys-footer-logo-link"
            aria-label="SYS – Strengthen Your Skills"
          >
            <span className="sys-footer-mark">
              <Image
                src="/branding/sys-v2/logos/SYS_Symbol_Compact_Transparent.png"
                alt=""
                width={48}
                height={48}
                className="sys-footer-logo"
              />
            </span>
            <span className="sys-footer-brand-copy">
              <strong>SYS – Strengthen Your Skills</strong>
              <small>AI-Powered Learning Platform</small>
            </span>
          </Link>

          <p className="sys-footer-description">
            AI-powered learning, assessment and student support in one connected journey.
          </p>
        </div>

        {/* Platform */}
        <div className="sys-footer-column">
          <h3>Platform</h3>

          {QUICK_LINKS.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </div>

        {/* Learning */}
        <div className="sys-footer-column">
          <h3>Learning</h3>

          {PLATFORM_LINKS.map((item) => (
            <Link key={item.label} href={item.href}>
              {item.label}
            </Link>
          ))}

          {authenticated ? (
            <>
              <Link href={dashboardPath}>Dashboard</Link>
              <Link href="/notifications">Notifications</Link>

              <button type="button" onClick={logout}>
                Log out
              </button>
            </>
          ) : session.status === "anonymous" ? (
            <Link href="/login">Login to SYS</Link>
          ) : null}
        </div>
      </div>

      <div className="sys-footer-bottom">
        <span>
          © {new Date().getFullYear()} SYS – Strengthen Your Skills. All rights
          reserved.
        </span>

        <span>Conceived and developed by <strong>Dr. Sudhakar Bolleddu</strong></span>
        <span>Shape Your Successful Future.</span>
      </div>

      <style jsx>{`
        .sys-footer {
          position: relative;
          background:
            radial-gradient(
              circle at 75% 0%,
              rgba(89, 45, 185, 0.18),
              transparent 32%
            ),
            linear-gradient(
              135deg,
              #050722 0%,
              #090936 55%,
              #15082f 100%
            );
          color: #d8dcf0;
          border-top: 1px solid rgba(111, 90, 255, 0.25);
        }

        .sys-footer-main {
          width: min(1180px, calc(100% - 48px));
          margin: 0 auto;
          padding: 30px 0 24px;
          display: grid;
          grid-template-columns: 2fr 1fr 1.25fr;
          gap: 42px;
        }

        .sys-footer-brand {
          max-width: 390px;
        }

        .sys-footer-logo-link {
          display: inline-flex;
          align-items: center;
          gap: 11px;
          text-decoration: none;
        }

        .sys-footer-mark {
          width: 50px;
          height: 50px;
          display: grid;
          place-items: center;
          flex: 0 0 50px;
          border: 1px solid rgba(255, 255, 255, 0.35);
          border-radius: 12px;
          background: #fff;
        }

        .sys-footer-logo {
          display: block;
          width: 43px;
          height: 43px;
          object-fit: contain;
        }

        .sys-footer-brand-copy {
          display: grid;
          gap: 4px;
        }

        .sys-footer-brand-copy strong {
          color: #fff;
          font-size: 13px;
          line-height: 1.2;
        }

        .sys-footer-brand-copy small {
          color: #aebde0;
          font-size: 9px;
        }

        .sys-footer-description {
          max-width: 370px;
          margin: 11px 0 0;
          color: #9da5c5;
          font-size: 13px;
          line-height: 1.6;
        }

        .sys-footer-column {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }

        .sys-footer-column h3 {
          margin: 0 0 4px;
          color: #ffffff;
          font-size: 14px;
          font-weight: 800;
        }

        .sys-footer-column a,
        .sys-footer-column button {
          color: #aab1cc;
          text-decoration: none;
          font-size: 13px;
          line-height: 1.4;
          transition:
            color 0.2s ease,
            transform 0.2s ease;
        }

        .sys-footer-column button {
          padding: 0;
          border: 0;
          background: transparent;
          font-family: inherit;
          cursor: pointer;
          text-align: left;
        }

        .sys-footer-column a:hover,
        .sys-footer-column button:hover {
          color: #ffffff;
          transform: translateX(2px);
        }

        .sys-footer-bottom {
          width: min(1180px, calc(100% - 48px));
          margin: 0 auto;
          padding: 13px 0 15px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 25px;
          color: #737c9d;
          font-size: 11px;
          line-height: 1.5;
        }

        .sys-footer-bottom strong {
          color: #c7d0e6;
          font-weight: 700;
        }

        @media (max-width: 900px) {
          .sys-footer-main {
            grid-template-columns: 1.5fr 1fr 1fr;
            gap: 28px;
          }

          .sys-footer-brand {
            grid-column: 1 / -1;
            max-width: 600px;
          }
        }

        @media (max-width: 600px) {
          .sys-footer-main {
            width: calc(100% - 32px);
            grid-template-columns: repeat(2, 1fr);
            padding: 27px 0 22px;
            gap: 26px 22px;
          }

          .sys-footer-brand {
            grid-column: 1 / -1;
          }

          .sys-footer-bottom {
            width: calc(100% - 32px);
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }
        }

        @media (max-width: 400px) {
          .sys-footer-main {
            grid-template-columns: 1fr;
          }

          .sys-footer-brand {
            grid-column: auto;
          }
        }
      `}</style>
    </footer>
  );
}
