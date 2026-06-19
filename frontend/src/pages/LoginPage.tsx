import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link } from "@tanstack/react-router";
import { Typography, Button } from "@material-tailwind/react";
import AppNavbar from "@/components/AppNavbar";
import { useAuth } from "@/hooks/useAuth";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, loginError, isLoggingIn } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (data: LoginFormValues) => {
    login(data);
  };

  return (
    <div className="bg-white min-h-screen">
      <AppNavbar />
      <section className="grid min-h-[calc(100vh-68px)] lg:grid-cols-2">
        <div className="my-auto p-8 text-center sm:p-10 md:p-20 xl:px-32 xl:py-24">
          <Typography variant="h3" color="blue-gray" className="mb-2">
            Welcome back
          </Typography>
          <Typography className="font-normal mb-16 text-blue-gray-800">
            Welcome back, please enter your details.
          </Typography>

          <form
            onSubmit={handleSubmit(onSubmit)}
            className="mx-auto max-w-[24rem] text-left"
          >
            <div className="mb-4">
              <label className="block text-sm font-medium text-blue-gray-700 mb-1">
                Username or Email
              </label>
              <input
                type="text"
                autoComplete="username"
                placeholder="you@example.com"
                className="w-full px-3 py-3 border border-blue-gray-200 rounded-lg text-blue-gray-900 placeholder-blue-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                {...register("username")}
              />
              {errors.username && (
                <p className="mt-1 text-xs text-red-500">{errors.username.message}</p>
              )}
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-blue-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full px-3 py-3 border border-blue-gray-200 rounded-lg text-blue-gray-900 placeholder-blue-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                {...register("password")}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <Typography as="a" href="#" color="blue-gray" className="font-medium text-sm">
                Forgot password?
              </Typography>
            </div>

            {loginError && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
                <p className="text-sm text-red-600">{loginError.message}</p>
              </div>
            )}

            <Button
              color={"dark" as any}
              size="lg"
              className="mt-2 w-full"
              type="submit"
              disabled={isLoggingIn}
            >
              {isLoggingIn ? "Signing in..." : "sign in"}
            </Button>

            <Typography color="gray" className="mt-6 text-center font-normal">
              Don&apos;t have an account?{" "}
              <Link
                to="/signup"
                className="font-medium text-dark transition-colors hover:text-blue-700"
              >
                Sign up
              </Link>
            </Typography>
          </form>
        </div>

        <img
          src="/login_side.png"
          alt="background"
          className="hidden h-[calc(100vh-68px)] w-full object-cover lg:block"
        />
      </section>
    </div>
  );
}
