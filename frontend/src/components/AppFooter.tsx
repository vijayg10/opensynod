import { Typography } from "@material-tailwind/react";

const currentYear = new Date().getFullYear();

export default function AppFooter() {
  return (
    <footer className="mt-10 px-8 py-6 border-t border-blue-gray-50">
      <div className="container mx-auto flex justify-center">
        <Typography color="gray" className="text-center font-normal">
          &copy; {currentYear} OpenSynod. All rights reserved.
        </Typography>
      </div>
    </footer>
  );
}
