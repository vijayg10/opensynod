import { Link } from "@tanstack/react-router";
import { Button, Typography } from "@material-tailwind/react";
import { ArrowSmallRightIcon } from "@heroicons/react/24/outline";
import AppNavbar from "@/components/AppNavbar";
import AppFooter from "@/components/AppFooter";
import { FeatureSection } from "@/components/team/FeatureSection";

function HeroSection() {
  return (
    <header className="h-full w-full bg-white px-8 py-28">
      <div className="container mx-auto grid items-center lg:grid-cols-2">
        <div className="text-center lg:text-left">
          <div className="mb-8 inline-flex items-center rounded-lg border border-dark/30 py-1 pl-1 pr-3">
            <Typography
              variant="small"
              className="mr-3 rounded-md bg-dark py-0.5 px-3 font-medium text-white"
            >
              New
            </Typography>
            <Typography
              color={"dark" as any}
              variant="small"
              className="!flex !items-center !font-semibold"
            >
              Multi-AI panel debates now live
              <ArrowSmallRightIcon className="ml-1.5 h-4 w-4" strokeWidth={3} />
            </Typography>
          </div>
          <Typography
            variant="h1"
            color="blue-gray"
            className="mb-8 leading-tight lg:text-6xl"
          >
            OpenSynod — where ideas meet debate
          </Typography>
          <Typography variant="lead" className="lg:pr-20 text-blue-gray-800">
            Orchestrate intelligent panel discussions with AI experts from any
            field. Set your topic, choose your panelists, and watch perspectives
            unfold in real time.
          </Typography>
          <div className="mt-12 flex flex-wrap justify-center gap-3 lg:justify-start">
            <Link to="/">
              <Button color={"dark" as any} className="flex items-center gap-2">
                Go to Dashboard
              </Button>
            </Link>
            <Link to="/signup">
              <Button variant="outlined" color="blue-gray" className="flex items-center gap-2">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>
        <div className="hidden lg:flex">
          <img
            src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
            alt="Team collaboration"
            className="max-w-md rounded-3xl ml-auto object-cover h-96 w-full"
          />
        </div>
      </div>
    </header>
  );
}

export default function OurTeamPage() {
  return (
    <div className="bg-white min-h-screen">
      <AppNavbar />
      <HeroSection />
      <FeatureSection />
      <AppFooter />
    </div>
  );
}
