// /**
//  * SYS Common Header
//  * -----------------
//  * Shared authenticated/anonymous header for all SYS users.
//  *
//  * Responsibilities:
//  * - Display SYS branding.
//  * - Provide role-aware Home navigation.
//  * - Display Notifications for authenticated users.
//  * - Display authenticated user's photo, name and role.
//  * - Provide logout functionality.
//  * - Provide responsive mobile navigation.
//  *
//  * Authentication contract:
//  * - Uses the existing Layout -> /auth/me session.
//  * - Does not perform its own API request.
//  */

// import Image from "next/image";
// import Link from "next/link";
// import { useRouter } from "next/router";
// import { useState } from "react";
// import { clearSession, roleDisplayLabel, roleLandingPath } from "../../src/auth";

// const NAV_ITEMS = [
//   { label: "Home", href: "/" },
// ];

// function getInitials(name) {
//   const normalized = typeof name === "string" ? name.trim() : "";

//   if (!normalized) {
//     return "SYS";
//   }

//   const parts = normalized.split(/\s+/).filter(Boolean);

//   if (parts.length === 1) {
//     return parts[0].slice(0, 2).toUpperCase();
//   }

//   return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
// }

// function resolvePhotoUrl(photoUrl) {
//   if (!photoUrl || typeof photoUrl !== "string") {
//     return null;
//   }

//   const value = photoUrl.trim();

//   if (!value) {
//     return null;
//   }

//   /*
//    * Backend may return either:
//    *   https://...
//    *   /uploads/...
//    *   uploads/...
//    *
//    * Keep absolute URLs unchanged.
//    * Convert relative API paths to the configured API origin.
//    */
//   if (/^https?:\/\//i.test(value)) {
//     return value;
//   }

//   const apiBaseUrl =
//     process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

//   const normalizedPath = value.startsWith("/") ? value : `/${value}`;

//   return `${apiBaseUrl.replace(/\/$/, "")}${normalizedPath}`;
// }

// export default function SYSHeader({
//   session = { status: "anonymous", user: null },
// }) {
//   const router = useRouter();
//   const [menuOpen, setMenuOpen] = useState(false);
//   const [profileOpen, setProfileOpen] = useState(false);
//   const [photoError, setPhotoError] = useState(false);

//   const authenticated =
//     session.status === "authenticated" && Boolean(session.user);

//   const user = authenticated ? session.user : null;

//   const dashboardPath = authenticated
//     ? roleLandingPath(user?.role) || "/dashboard"
//     : "/";

//   const photoUrl = resolvePhotoUrl(user?.photo_url);
//   const showPhoto = Boolean(photoUrl) && !photoError;

//   const homeHref = authenticated ? dashboardPath : "/";

//   const isActive = (href) => {
//     if (authenticated && href === "/") {
//       return (
//         router.pathname === dashboardPath ||
//         (dashboardPath !== "/" &&
//           router.pathname.startsWith(`${dashboardPath}/`))
//       );
//     }

//     if (href === "/") {
//       return router.pathname === "/";
//     }

//     return (
//       router.pathname === href ||
//       router.pathname.startsWith(`${href}/`)
//     );
//   };

//   const closeMenu = () => {
//     setMenuOpen(false);
//   };

//   const logout = () => {
//     clearSession();
//     setMenuOpen(false);
//     setProfileOpen(false);
//     window.location.href = "/login?reason=signed-out";
//   };

//   const displayName = user?.name?.trim() || "SYS User";
//   const displayRole = roleDisplayLabel(user?.role);

//   return (
//     <header className="sys-header">
//       <div className="sys-header-inner">
//         {/* Brand */}
//         <Link
//           href="/"
//           className="sys-brand"
//           aria-label="SYS – Strengthen Your Skills"
//           onClick={closeMenu}
//         >
//           <Image
//             src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
//             alt="SYS – Strengthen Your Skills"
//             width={330}
//             height={92}
//             preload
//             className="sys-brand-logo"
//           />
//         </Link>

//         {/* Desktop Navigation */}
//         <nav className="sys-desktop-nav" aria-label="Main navigation">
//           <Link
//             href={homeHref}
//             className={`sys-nav-link ${
//               isActive("/") ? "active" : ""
//             }`}
//           >
//             Home
//           </Link>

//           {authenticated ? (
//             <>
//               <Link
//                 href="/notifications"
//                 className={`sys-nav-link ${
//                   router.pathname === "/notifications" ||
//                   router.pathname.startsWith("/notifications/")
//                     ? "active"
//                     : ""
//                 }`}
//               >
//                 Notifications
//               </Link>

//               <span
//                 className="sys-nav-divider"
//                 aria-hidden="true"
//               />

//               {/* User Profile */}
//               <div className="sys-profile">
//                 <button
//                   type="button"
//                   className="sys-profile-button"
//                   aria-expanded={profileOpen}
//                   aria-controls="sys-profile-menu"
//                   onClick={() =>
//                     setProfileOpen((value) => !value)
//                   }
//                 >
//                   <span className="sys-avatar" aria-hidden="true">
//                     {showPhoto ? (
//                       <img
//                         src={photoUrl}
//                         alt=""
//                         className="sys-avatar-image"
//                         onError={() => setPhotoError(true)}
//                       />
//                     ) : (
//                       <span className="sys-avatar-initials">
//                         {getInitials(displayName)}
//                       </span>
//                     )}
//                   </span>

//                   <span className="sys-profile-copy">
//                     <strong>{displayName}</strong>
//                     <small>{displayRole}</small>
//                   </span>

//                   <span
//                     className={`sys-profile-chevron ${
//                       profileOpen ? "open" : ""
//                     }`}
//                     aria-hidden="true"
//                   >
//                     ▾
//                   </span>
//                 </button>

//                 {profileOpen && (
//                   <div
//                     id="sys-profile-menu"
//                     className="sys-profile-menu"
//                   >
//                     <div className="sys-profile-menu-user">
//                       <span className="sys-menu-avatar">
//                         {showPhoto ? (
//                           <img
//                             src={photoUrl}
//                             alt=""
//                             className="sys-avatar-image"
//                             onError={() => setPhotoError(true)}
//                           />
//                         ) : (
//                           <span className="sys-avatar-initials">
//                             {getInitials(displayName)}
//                           </span>
//                         )}
//                       </span>

//                       <div>
//                         <strong>{displayName}</strong>
//                         <span>{displayRole}</span>
//                       </div>
//                     </div>
                    
//                     <div className="sys-profile-menu-divider" />


//                     <div className="sys-profile-menu-actions">
//                         <Link
//                           href={dashboardPath}
//                           onClick={() => setProfileOpen(false)}
//                         >
//                           Dashboard
//                         </Link>

//                         <Link
//                           href="/notifications"
//                           onClick={() => setProfileOpen(false)}
//                         >
//                           Notifications
//                         </Link>

//                         <button
//                           type="button"
//                           onClick={logout}
//                         >
//                           Log out
//                         </button>
//                       </div>
//                     {/* <Link
//                       href={dashboardPath}
//                       onClick={() => setProfileOpen(false)}
//                     >
//                       Dashboard
//                     </Link>

//                     <Link
//                       href="/notifications"
//                       onClick={() => setProfileOpen(false)}
//                     >
//                       Notifications
//                     </Link>

//                     <button
//                       type="button"
//                       onClick={logout}
//                     >
//                       Log out
//                     </button> */}
//                   </div>
//                 )}
//               </div>
//             </>
//           ) : session.status === "anonymous" ? (
//             <Link href="/login" className="sys-login-button">
//               Login
//             </Link>
//           ) : null}
//         </nav>

//         {/* Mobile Menu Button */}
//         <button
//           type="button"
//           className="sys-menu-button"
//           aria-label={
//             menuOpen
//               ? "Close navigation menu"
//               : "Open navigation menu"
//           }
//           aria-expanded={menuOpen}
//           onClick={() => setMenuOpen((value) => !value)}
//         >
//           <span />
//           <span />
//           <span />
//         </button>
//       </div>

//       {/* Mobile Navigation */}
//       {menuOpen && (
//         <nav className="sys-mobile-nav" aria-label="Mobile navigation">
//           <Link
//             href={homeHref}
//             className={`sys-mobile-link ${
//               isActive("/") ? "active" : ""
//             }`}
//             onClick={closeMenu}
//           >
//             Home
//           </Link>

//           {authenticated ? (
//             <>
//               <Link
//                 href="/notifications"
//                 className={`sys-mobile-link ${
//                   router.pathname === "/notifications"
//                     ? "active"
//                     : ""
//                 }`}
//                 onClick={closeMenu}
//               >
//                 Notifications
//               </Link>

//               <div className="sys-mobile-user">
//                 <span className="sys-mobile-avatar">
//                   {showPhoto ? (
//                     <img
//                       src={photoUrl}
//                       alt=""
//                       className="sys-avatar-image"
//                       onError={() => setPhotoError(true)}
//                     />
//                   ) : (
//                     <span className="sys-avatar-initials">
//                       {getInitials(displayName)}
//                     </span>
//                   )}
//                 </span>

//                 <span className="sys-mobile-user-copy">
//                   <strong>{displayName}</strong>
//                   <small>{displayRole}</small>
//                 </span>
//               </div>

//               <button
//                 type="button"
//                 className="sys-mobile-login"
//                 onClick={logout}
//               >
//                 Log out
//               </button>
//             </>
//           ) : session.status === "anonymous" ? (
//             <Link
//               href="/login"
//               className="sys-mobile-login"
//               onClick={closeMenu}
//             >
//               Login
//             </Link>
//           ) : null}
//         </nav>
//       )}

//       <style jsx>{`
//         .sys-header {
//           position: sticky;
//           top: 0;
//           z-index: 1000;
//           width: 100%;
//           background:
//             linear-gradient(
//               105deg,
//               rgba(7, 10, 48, 0.98) 0%,
//               rgba(13, 12, 65, 0.98) 52%,
//               rgba(31, 8, 78, 0.98) 100%
//             );
//           border-bottom: 1px solid rgba(132, 108, 255, 0.28);
//           box-shadow: 0 8px 30px rgba(3, 4, 25, 0.22);
//           backdrop-filter: blur(16px);
//         }

//         .sys-header-inner {
//           width: min(1280px, calc(100% - 48px));
//           min-height: 82px;
//           margin: 0 auto;
//           display: flex;
//           align-items: center;
//           justify-content: space-between;
//           gap: 32px;
//         }

//         .sys-brand {
//           display: inline-flex;
//           align-items: center;
//           flex-shrink: 0;
//           text-decoration: none;
//         }

//         .sys-brand-logo {
//           display: block;
//           width: 265px;
//           height: auto;
//           object-fit: contain;
//         }

//         .sys-desktop-nav {
//           display: flex;
//           align-items: center;
//           justify-content: flex-end;
//           gap: 28px;
//         }

//         .sys-nav-link {
//           position: relative;
//           display: inline-flex;
//           align-items: center;
//           padding: 29px 0;
//           color: #ffffff !important;
//           text-decoration: none !important;
//           font-size: 14px;
//           font-weight: 700;
//           white-space: nowrap;
//           opacity: 1 !important;
//           transition:
//             color 0.2s ease,
//             transform 0.2s ease;
//         }

//         .sys-nav-link::after {
//           content: "";
//           position: absolute;
//           left: 0;
//           right: 0;
//           bottom: 18px;
//           height: 2px;
//           border-radius: 999px;
//           background: linear-gradient(
//             90deg,
//             #2f7cff,
//             #c72cff
//           );
//           transform: scaleX(0);
//           transform-origin: center;
//           transition: transform 0.2s ease;
//         }

//         .sys-nav-link:hover {
//           color: #ffffff !important;
//           transform: translateY(-1px);
//         }

//         .sys-nav-link:hover::after,
//         .sys-nav-link.active::after {
//           transform: scaleX(1);
//         }

//         a.sys-nav-link,
//         a.sys-nav-link:visited {
//         color: #ffffff !important;
//         }

//         a.sys-nav-link:hover,
//         a.sys-nav-link:focus,
//         a.sys-nav-link:active,
//         a.sys-nav-link.active {
//         color: #ffffff !important;
//         }


//         .sys-nav-link.active {
//           color: #ffffff !important;
//         }

//         .sys-nav-divider {
//           width: 1px;
//           height: 30px;
//           background: rgba(255, 255, 255, 0.22);
//         }

//         /* -------------------------------------------------
//            User profile
//            ------------------------------------------------- */

//         .sys-profile {
//           position: relative;
//         }

//         .sys-profile-button {
//           display: inline-flex;
//           align-items: center;
//           gap: 10px;
//           min-height: 48px;
//           padding: 4px 8px 4px 5px;
//           border: 1px solid transparent;
//           border-radius: 12px;
//           color: #ffffff;
//           background: transparent;
//           cursor: pointer;
//           transition:
//             background 0.2s ease,
//             border-color 0.2s ease;
//         }

//         .sys-profile-button:hover,
//         .sys-profile-button[aria-expanded="true"] {
//           background: rgba(255, 255, 255, 0.08);
//           border-color: rgba(193, 191, 255, 0.25);
//         }

//         .sys-avatar {
//           width: 38px;
//           height: 38px;
//           flex: 0 0 38px;
//           display: inline-flex;
//           align-items: center;
//           justify-content: center;
//           overflow: hidden;
//           border-radius: 50%;
//           border: 2px solid rgba(255, 255, 255, 0.7);
//           background:
//             linear-gradient(
//               135deg,
//               #2f7cff,
//               #8d42ff,
//               #c72cff
//             );
//           box-shadow:
//             0 3px 12px rgba(0, 0, 0, 0.25);
//         }

//         .sys-avatar-image {
//           display: block;
//           width: 100%;
//           height: 100%;
//           object-fit: cover;
//         }

//         .sys-avatar-initials {
//           display: inline-flex;
//           align-items: center;
//           justify-content: center;
//           width: 100%;
//           height: 100%;
//           color: #ffffff;
//           font-size: 12px;
//           font-weight: 800;
//           letter-spacing: 0.02em;
//         }

//         .sys-profile-copy {
//           display: flex;
//           flex-direction: column;
//           align-items: flex-start;
//           justify-content: center;
//           min-width: 110px;
//           max-width: 190px;
//           line-height: 1.15;
//         }

//         .sys-profile-copy strong {
//           overflow: hidden;
//           width: 100%;
//           color: #ffffff;
//           font-size: 13px;
//           font-weight: 700;
//           text-overflow: ellipsis;
//           white-space: nowrap;
//         }

//         .sys-profile-copy small {
//           margin-top: 4px;
//           color: #cfd3f4;
//           font-size: 11px;
//           font-weight: 600;
//         }

//         .sys-profile-chevron {
//           margin-left: 2px;
//           color: #dce0ff;
//           font-size: 15px;
//           transition: transform 0.2s ease;
//         }

//         .sys-profile-chevron.open {
//           transform: rotate(180deg);
//         }

//         .sys-profile-menu {
//           position: absolute;
//           top: calc(100% + 10px);
//           right: 0;
//           width: 270px;
//           box-sizing: border-box;
//           padding: 10px;
//           border: 1px solid rgba(145, 130, 255, 0.28);
//           border-radius: 14px;
//           background:
//             linear-gradient(
//               145deg,
//               rgba(11, 14, 57, 0.99),
//               rgba(28, 13, 66, 0.99)
//             );
//           box-shadow:
//             0 18px 45px rgba(3, 4, 25, 0.4);
//         }

//         .sys-profile-menu-user {
//           display: flex;
//           align-items: center;
//           gap: 10px;
//           padding: 8px;
//         }

//         .sys-menu-avatar {
//           width: 42px;
//           height: 42px;
//           flex: 0 0 42px;
//           display: inline-flex;
//           align-items: center;
//           justify-content: center;
//           overflow: hidden;
//           border-radius: 50%;
//           background:
//             linear-gradient(
//               135deg,
//               #2f7cff,
//               #8d42ff,
//               #c72cff
//             );
//         }

//         .sys-profile-menu-user > div {
//           min-width: 0;
//           display: flex;
//           flex-direction: column;
//         }

//         .sys-profile-menu-user strong {
//           overflow: hidden;
//           color: #ffffff;
//           font-size: 13px;
//           text-overflow: ellipsis;
//           white-space: nowrap;
//         }

//         .sys-profile-menu-user span {
//           margin-top: 3px;
//           color: #bfc4e8;
//           font-size: 11px;
//           font-weight: 600;
//         }

//         .sys-profile-menu-divider {
//           height: 1px;
//           margin: 8px 4px;
//           background: rgba(255, 255, 255, 0.1);
//         }

//         .sys-profile-menu a,
//         .sys-profile-menu button {
//           display: flex;
//           width: 100%;
//           align-items: center;
//           padding: 10px 12px;
//           border: 0;
//           border-radius: 8px;
//           color: #ffffff;
//           background: transparent;
//           text-decoration: none;
//           font-family: inherit;
//           font-size: 13px;
//           font-weight: 600;
//           text-align: left;
//           cursor: pointer;
//         }

//         .sys-profile-menu a:hover,
//         .sys-profile-menu button:hover {
//           color: #ffffff;
//           background: rgba(104, 75, 235, 0.2);
//         }

//         .sys-profile-menu button {
//           color: #ffffff;
//         }

//         .sys-profile-menu button:hover {
//           color: #ffffff;
//           background: rgba(220, 50, 90, 0.2);
//         }

//         .sys-profile-menu-actions {
//           display: flex;
//           flex-direction: column;
//           gap: 4px;
//           width: 100%;
//         }

//         .sys-profile-menu-actions > a,
//         .sys-profile-menu-actions > button {
//           display: flex !important;
//           width: 100% !important;
//           min-height: 40px;
//           align-items: center;
//           justify-content: flex-start;
//           box-sizing: border-box;
//           padding: 10px 12px;
//           margin: 0;
//           white-space: nowrap;
//         }


//         .sys-profile-menu-actions > a {
//             color: #ffffff;
//           }

//           .sys-profile-menu-actions > a:hover {
//             color: #ffffff;
//             background: rgba(104, 75, 235, 0.25);
//           }






//         /* -------------------------------------------------
//            Login
//            ------------------------------------------------- */

//         .sys-login-button {
//           display: inline-flex;
//           align-items: center;
//           justify-content: center;
//           min-width: 92px;
//           min-height: 42px;
//           padding: 0 20px;
//           border: 1px solid rgba(193, 191, 255, 0.8);
//           border-radius: 11px;
//           color: #ffffff;
//           background: rgba(255, 255, 255, 0.03);
//           text-decoration: none;
//           font-size: 14px;
//           font-weight: 700;
//           transition:
//             transform 0.2s ease,
//             border-color 0.2s ease,
//             background 0.2s ease,
//             box-shadow 0.2s ease;
//         }

//         .sys-login-button:hover {
//           transform: translateY(-1px);
//           border-color: #8e70ff;
//           background: rgba(91, 67, 220, 0.25);
//           box-shadow: 0 8px 25px rgba(92, 65, 255, 0.25);
//         }

//         /* -------------------------------------------------
//            Mobile
//            ------------------------------------------------- */

//         .sys-menu-button {
//           display: none;
//           width: 44px;
//           height: 44px;
//           padding: 10px;
//           border: 1px solid rgba(255, 255, 255, 0.2);
//           border-radius: 10px;
//           background: rgba(255, 255, 255, 0.05);
//           cursor: pointer;
//         }

//         .sys-menu-button span {
//           display: block;
//           width: 100%;
//           height: 2px;
//           margin: 5px 0;
//           border-radius: 999px;
//           background: #ffffff;
//         }

//         .sys-mobile-nav {
//           display: none;
//         }

//         .sys-mobile-user {
//           display: flex;
//           align-items: center;
//           gap: 11px;
//           margin-top: 8px;
//           padding: 12px 14px;
//           border-top: 1px solid rgba(255, 255, 255, 0.1);
//         }

//         .sys-mobile-avatar {
//           width: 38px;
//           height: 38px;
//           flex: 0 0 38px;
//           display: inline-flex;
//           align-items: center;
//           justify-content: center;
//           overflow: hidden;
//           border-radius: 50%;
//           border: 2px solid rgba(255, 255, 255, 0.6);
//           background:
//             linear-gradient(
//               135deg,
//               #2f7cff,
//               #8d42ff,
//               #c72cff
//             );
//         }

//         .sys-mobile-user-copy {
//           display: flex;
//           flex-direction: column;
//         }

//         .sys-mobile-user-copy strong {
//           color: #ffffff;
//           font-size: 14px;
//           font-weight: 700;
//         }

//         .sys-mobile-user-copy small {
//           margin-top: 3px;
//           color: #cfd3f4;
//           font-size: 11px;
//           font-weight: 600;
//         }

//         .sys-mobile-link {
//           opacity: 1 !important;
//           display: block;
//           padding: 13px 14px;
//           border-radius: 9px;
//           color: #ffffff !important;
//           text-decoration: none !important;
//           font-size: 15px;
//           font-weight: 600;
//         }

//         .sys-mobile-link:hover,
//         .sys-mobile-link.active {
//         color: #ffffff !important;
//           background: rgba(104, 75, 235, 0.2);
//         }

//         .sys-mobile-login {
//           display: inline-flex;
//           align-items: center;
//           justify-content: center;
//           margin-top: 8px;
//           padding: 12px 18px;
//           border: 1px solid rgba(193, 191, 255, 0.75);
//           border-radius: 10px;
//           color: #ffffff !important;
//           background: transparent;
//           text-decoration: none;
//           font-family: inherit;
//           font-size: 14px;
//           font-weight: 700;
//           cursor: pointer;
//         }

//         @media (max-width: 1050px) {
//           .sys-header-inner {
//             width: min(100% - 32px, 1280px);
//           }

//           .sys-desktop-nav {
//             gap: 20px;
//           }

//           .sys-brand-logo {
//             width: 230px;
//           }

//           .sys-profile-copy {
//             max-width: 150px;
//           }
//         }

//         @media (max-width: 850px) {
//           .sys-header-inner {
//             min-height: 72px;
//           }

//           .sys-brand-logo {
//             width: 220px;
//           }

//           .sys-desktop-nav {
//             display: none;
//           }

//           .sys-menu-button {
//             display: block;
//           }

//           .sys-mobile-nav {
//             display: flex;
//             flex-direction: column;
//             gap: 4px;
//             width: min(100% - 32px, 1280px);
//             margin: 0 auto;
//             padding: 10px 0 18px;
//           }
//         }

//         @media (max-width: 480px) {
//           .sys-header-inner {
//             width: calc(100% - 24px);
//           }

//           .sys-brand-logo {
//             width: 195px;
//           }

//           .sys-mobile-nav {
//             width: calc(100% - 24px);
//           }
//         }
//       `}</style>
//     </header>
//   );
// }


import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";
import { clearSession, roleDisplayLabel, roleLandingPath } from "../../src/auth";

function getInitials(name) {
  const normalized = typeof name === "string" ? name.trim() : "";
  if (!normalized) return "SYS";
  const parts = normalized.split(/\s+/).filter(Boolean);
  return parts.length === 1
    ? parts[0].slice(0, 2).toUpperCase()
    : `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function resolvePhotoUrl(photoUrl) {
  if (!photoUrl || typeof photoUrl !== "string") return null;
  const value = photoUrl.trim();
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) return value;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
  const normalizedPath = value.startsWith("/") ? value : `/${value}`;
  return `${apiBaseUrl.replace(/\/$/, "")}${normalizedPath}`;
}

export default function SYSHeader({ session = { status: "anonymous", user: null } }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [photoError, setPhotoError] = useState(false);

  const authenticated = session.status === "authenticated" && Boolean(session.user);
  const user = authenticated ? session.user : null;
  const dashboardPath = authenticated ? roleLandingPath(user?.role) || "/dashboard" : "/";
  const photoUrl = resolvePhotoUrl(user?.photo_url);
  const showPhoto = Boolean(photoUrl) && !photoError;
  const homeHref = authenticated ? dashboardPath : "/";
  const displayName = user?.name?.trim() || "SYS User";
  const displayRole = roleDisplayLabel(user?.role);

  const logout = () => {
    clearSession();
    setMenuOpen(false);
    setProfileOpen(false);
    window.location.href = "/login?reason=signed-out";
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-gradient-to-r from-indigo-950 via-indigo-900 to-purple-900 border-b border-indigo-400/30 shadow-lg backdrop-blur-md">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 h-20">
        {/* Brand */}
        <Link href={homeHref} className="flex items-center gap-3">
          <Image
            src="/branding/sys-v2/logos/SYS_Header_Logo_Dark.png"
            alt="SYS – Strengthen Your Skills"
            width={220}
            height={72}
            className="object-contain"
          />
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-6 text-white font-semibold">
          <Link href={homeHref} className="hover:text-blue-300">Home</Link>
          {authenticated && (
            <>
              <Link href="/notifications" className="hover:text-blue-300">Notifications</Link>
              <div className="w-px h-6 bg-white/30" />
              {/* Profile */}
              <div className="relative">
                <button
                  type="button"
                  className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-white/10"
                  onClick={() => setProfileOpen((v) => !v)}
                >
                  <span className="w-9 h-9 rounded-full border-2 border-white/70 bg-gradient-to-tr from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center text-white font-bold">
                    {showPhoto ? (
                      <img
                        src={photoUrl}
                        alt=""
                        className="w-full h-full rounded-full object-cover"
                        onError={() => setPhotoError(true)}
                      />
                    ) : (
                      getInitials(displayName)
                    )}
                  </span>
                  <span className="flex flex-col text-left">
                    <strong className="text-sm truncate">{displayName}</strong>
                    <small className="text-xs text-indigo-200">{displayRole}</small>
                  </span>
                  <span className={`ml-1 text-indigo-200 transition-transform ${profileOpen ? "rotate-180" : ""}`}>
                    ▾
                  </span>
                </button>

                {profileOpen && (
                  <div className="absolute right-0 mt-2 w-64 rounded-lg bg-gradient-to-br from-indigo-950 to-purple-900 shadow-xl p-3 text-white">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center">
                        {showPhoto ? (
                          <img
                            src={photoUrl}
                            alt=""
                            className="w-full h-full rounded-full object-cover"
                            onError={() => setPhotoError(true)}
                          />
                        ) : (
                          getInitials(displayName)
                        )}
                      </span>
                      <div>
                        <strong className="text-sm">{displayName}</strong>
                        <span className="block text-xs text-indigo-200">{displayRole}</span>
                      </div>
                    </div>
                    <div className="border-t border-white/20 my-2" />
                    <div className="flex flex-col gap-1">
                      <Link href={dashboardPath} onClick={() => setProfileOpen(false)} className="px-3 py-2 rounded hover:bg-indigo-700/50">Dashboard</Link>
                      <Link href="/notifications" onClick={() => setProfileOpen(false)} className="px-3 py-2 rounded hover:bg-indigo-700/50">Notifications</Link>
                      <button onClick={logout} className="px-3 py-2 rounded hover:bg-red-700/50 text-left">Log out</button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
          {!authenticated && session.status === "anonymous" && (
            <Link href="/login" className="px-4 py-2 rounded-lg border border-indigo-400 text-white hover:bg-indigo-700/50">
              Login
            </Link>
          )}
        </nav>

        {/* Mobile Menu Button */}
        <button
          type="button"
          className="md:hidden w-10 h-10 flex flex-col justify-center items-center gap-1 rounded-lg border border-white/30 bg-white/10 text-white"
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span className="w-6 h-0.5 bg-white rounded" />
          <span className="w-6 h-0.5 bg-white rounded" />
          <span className="w-6 h-0.5 bg-white rounded" />
        </button>
      </div>

      {/* Mobile Nav */}
      {menuOpen && (
        <nav className="md:hidden flex flex-col gap-2 px-6 pb-4 text-white font-semibold bg-gradient-to-br from-indigo-950 to-purple-900">
          <Link href={homeHref} onClick={() => setMenuOpen(false)} className="px-3 py-2 rounded hover:bg-indigo-700/50">Home</Link>
          {authenticated ? (
            <>
              <Link href="/notifications" onClick={() => setMenuOpen(false)} className="px-3 py-2 rounded hover:bg-indigo-700/50">Notifications</Link>
              <div className="flex items-center gap-3 border-t border-white/20 pt-3">
                <span className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center text-white font-bold">
                  {showPhoto ? (
                    <img
                      src={photoUrl}
                      alt=""
                      className="w-full h-full rounded-full object-cover"
                      onError={() => setPhotoError(true)}
                    />
                  ) : (
                    getInitials(displayName)
                  )}
                </span>
                <span className="flex flex-col">
                  <strong className="text-sm">{displayName}</strong>
                  <small className="text-xs text-indigo-200">{displayRole}</small>
                </span>
              </div>
              <button onClick={logout} className="mt-2 px-3 py-2 rounded border border-indigo-400 hover:bg-red-700/50 text-left">Log out</button>
            </>
          ) : (
            <Link href="/login" onClick={() => setMenuOpen(false)} className="px-3 py-2 rounded border border-indigo-400 hover:bg-indigo-700/50">
              Login
            </Link>
          )}
        </nav>
      )}
    </header>
  );
}