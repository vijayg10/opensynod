import React from "react";
import { Link } from "@tanstack/react-router";
import {
  Navbar,
  Collapse,
  Button,
  IconButton,
} from "@material-tailwind/react";
import {
  Bars3Icon,
  XMarkIcon,
  Square3Stack3DIcon,
} from "@heroicons/react/24/outline";
import { useAuthStore } from "@/stores/auth-store";
import { apiJson } from "@/lib/api";

const navItems = [
  { label: "Dashboard", to: "/", icon: Square3Stack3DIcon },
] as const;

function NavList() {
  return (
    <ul className="list-none mt-2 mb-4 flex flex-col gap-2 lg:mb-0 lg:mt-0 lg:flex-row lg:items-center lg:gap-1">
      {navItems.map(({ label, to, icon: Icon }) => (
        <li key={to}>
          <Link
            to={to}
            className="flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium text-blue-gray-900 hover:bg-blue-gray-50 transition-colors"
          >
            <Icon className="h-[18px] w-[18px]" strokeWidth={1.5} />
            {label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function AppNavbar() {
  const [openNav, setOpenNav] = React.useState(false);
  const { isAuthenticated, clearAuth } = useAuthStore();

  React.useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 960) setOpenNav(false);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleLogout = async () => {
    try {
      await apiJson("/api/v1/auth/logout", { method: "POST" });
    } finally {
      clearAuth();
    }
  };

  return (
    <Navbar className="sticky top-0 z-10 h-max max-w-full rounded-none py-0 px-4 lg:px-8">
      <div className="flex items-center justify-between text-blue-gray-900">
        <Link to="/">
          <img
            src="/logos/opensynod_hlogo.png"
            alt="OpenSynod"
            className="mr-4 h-16 w-auto cursor-pointer"
          />
        </Link>
        <div className="hidden lg:block">
          <NavList />
        </div>
        <div className="hidden gap-2 lg:flex items-center">
          {isAuthenticated ? (
            <Button
              variant="text"
              size="sm"
              color="blue-gray"
              onClick={handleLogout}
            >
              Sign Out
            </Button>
          ) : (
            <Link to="/login">
              <Button size="sm" color={"dark" as any}>
                Sign In
              </Button>
            </Link>
          )}
        </div>
        <IconButton
          variant="text"
          className="ml-auto h-6 w-6 text-inherit hover:bg-transparent focus:bg-transparent active:bg-transparent lg:hidden"
          ripple={false}
          onClick={() => setOpenNav(!openNav)}
        >
          {openNav ? (
            <XMarkIcon className="h-6 w-6" strokeWidth={2} />
          ) : (
            <Bars3Icon className="h-6 w-6" strokeWidth={2} />
          )}
        </IconButton>
      </div>
      <Collapse open={openNav}>
        <NavList />
        <div className="flex items-center gap-x-1 pb-2">
          {isAuthenticated ? (
            <Button fullWidth variant="outlined" size="sm" color="blue-gray" onClick={handleLogout}>
              Sign Out
            </Button>
          ) : (
            <Link to="/login" className="flex-1">
              <Button fullWidth size="sm" color={"dark" as any}>
                Sign In
              </Button>
            </Link>
          )}
        </div>
      </Collapse>
    </Navbar>
  );
}
