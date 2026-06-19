import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link } from "@tanstack/react-router";
import { Typography, Button } from "@material-tailwind/react";
import AppNavbar from "@/components/AppNavbar";
import AppFooter from "@/components/AppFooter";
import { useAuth } from "@/hooks/useAuth";

const signupSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  display_name: z.string().optional(),
});

type SignupFormValues = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const { register: registerUser, registerError, isRegistering } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
  });

  const onSubmit = (data: SignupFormValues) => {
    registerUser(data);
  };

  return (
    <div className="bg-white min-h-screen">
      <AppNavbar />
      <section className="grid min-h-[calc(100vh-80px)] items-center p-8">
        <div className="text-center">
          <Typography variant="h3" color="blue-gray" className="mb-2">
            Join us today
          </Typography>
          <Typography className="font-normal mb-12 text-blue-gray-800">
            Create your account to start AI panel discussions with OpenSynod.
          </Typography>
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="mx-auto max-w-[24rem] text-left space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-blue-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                placeholder="yourname"
                className="w-full px-3 py-2.5 border border-blue-gray-200 rounded-lg text-blue-gray-900 placeholder-blue-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                {...register("username")}
              />
              {errors.username && (
                <p className="mt-1 text-xs text-red-500">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-blue-gray-700 mb-1">
                Display Name (optional)
              </label>
              <input
                type="text"
                placeholder="Your Full Name"
                className="w-full px-3 py-2.5 border border-blue-gray-200 rounded-lg text-blue-gray-900 placeholder-blue-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                {...register("display_name")}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-blue-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                className="w-full px-3 py-2.5 border border-blue-gray-200 rounded-lg text-blue-gray-900 placeholder-blue-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                {...register("email")}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-blue-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                className="w-full px-3 py-2.5 border border-blue-gray-200 rounded-lg text-blue-gray-900 placeholder-blue-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                {...register("password")}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            {registerError && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <p className="text-sm text-red-600">{registerError.message}</p>
              </div>
            )}

            <Button
              color={"dark" as any}
              size="lg"
              className="mt-2 w-full"
              type="submit"
              disabled={isRegistering}
            >
              {isRegistering ? "Creating account..." : "Get started"}
            </Button>

            <Typography color="gray" className="mt-6 text-center font-normal">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-medium text-dark transition-colors hover:text-blue-700"
              >
                Log in
              </Link>
            </Typography>
          </form>
        </div>
      </section>
      <AppFooter />
    </div>
  );
}
