import React from "react";
import { Card, CardBody, Typography } from "@material-tailwind/react";
import {
  EyeIcon,
  ChatBubbleOvalLeftEllipsisIcon,
  BoltIcon,
  FaceSmileIcon,
  LinkIcon,
  HeartIcon,
} from "@heroicons/react/24/solid";

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}

function FeatureCard({ icon, title, children }: FeatureCardProps) {
  return (
    <Card color="transparent" shadow={false}>
      <CardBody className="grid justify-center text-center">
        <div className="mx-auto mb-6 grid h-12 w-12 place-items-center rounded-full bg-dark p-2.5 text-white">
          {icon}
        </div>
        <Typography variant="h5" color="blue-gray" className="mb-2 !font-semibold">
          {title}
        </Typography>
        <Typography className="px-8 font-normal text-gray-700">
          {children}
        </Typography>
      </CardBody>
    </Card>
  );
}

const features = [
  {
    icon: <EyeIcon className="h-6 w-6" />,
    title: "AI Panel Debates",
    description:
      "Orchestrate multi-perspective AI discussions on any topic. Different AI personas debate and analyze from their unique viewpoints.",
  },
  {
    icon: <ChatBubbleOvalLeftEllipsisIcon className="h-6 w-6" />,
    title: "Real-Time Collaboration",
    description:
      "Watch AI panelists discuss live with streaming responses, creating a dynamic OpenSynod experience for any topic you choose.",
  },
  {
    icon: <BoltIcon className="h-6 w-6" />,
    title: "Instant Setup",
    description:
      "Start a discussion in seconds. Choose your topic, select your panel of AI experts, and let the debate begin.",
  },
  {
    icon: <FaceSmileIcon className="h-6 w-6" />,
    title: "Diverse Perspectives",
    description:
      "Explore every angle of an issue with AI panelists representing different fields, backgrounds, and viewpoints.",
  },
  {
    icon: <LinkIcon className="h-6 w-6" />,
    title: "Session Management",
    description:
      "Manage, pause, and resume discussions. Keep track of all your OpenSynod sessions and revisit insights anytime.",
  },
  {
    icon: <HeartIcon className="h-6 w-6" />,
    title: "Outcome Summaries",
    description:
      "Get structured summaries and outcomes from each session, turning complex debates into actionable insights.",
  },
];

export function FeatureSection() {
  return (
    <section className="py-28 px-4">
      <div className="container mx-auto mb-20 text-center">
        <Typography color={"dark" as any} className="mb-2 font-bold text-lg">
          What We Offer
        </Typography>
        <Typography variant="h2" color="blue-gray" className="mb-4">
          Turn any topic into a structured debate
        </Typography>
        <Typography
          variant="lead"
          className="mx-auto w-full px-4 text-blue-gray-800 md:w-10/12 lg:w-7/12 lg:px-8"
        >
          We&apos;re constantly trying to push the boundaries of AI collaboration.
          If you have a topic you want to explore deeply, we have the platform for you.
        </Typography>
      </div>
      <div className="container mx-auto grid grid-cols-1 gap-y-20 md:grid-cols-2 lg:grid-cols-3">
        {features.map(({ icon, title, description }) => (
          <FeatureCard key={title} icon={icon} title={title}>
            {description}
          </FeatureCard>
        ))}
      </div>
    </section>
  );
}

export default FeatureSection;
