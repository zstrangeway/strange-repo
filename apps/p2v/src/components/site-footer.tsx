export function SiteFooter({ facility = false }: { facility?: boolean }) {
  return (
    <footer>
      <div className="footer-top">
        <div className="brand-lockup">
          <a href="/" aria-label="P2V Basketball Academy home">
            <img
              src="/assets/forged-logo.png"
              alt="P2V Basketball Academy"
              loading="lazy"
            />
          </a>
        </div>
        <p>
          Built in the 608.
          <br />
          Ready for what’s next.
        </p>
        <a href="/contact.html">Let’s get to work</a>
      </div>
      <div className="footer-bottom">
        <span>© 2026 P2V Basketball Academy · Madison, Wisconsin</span>
        <a href="mailto:p2vacademy@gmail.com">p2vacademy@gmail.com</a>
        <span>
          {facility
            ? "Design preview · Facility photographs from P2V"
            : "Design preview · Illustrative basketball photography"}
        </span>
      </div>
    </footer>
  );
}
