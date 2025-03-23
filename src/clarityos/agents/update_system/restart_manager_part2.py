    async def _handle_restart_cancel(self, message):
        """Handle a restart cancellation request."""
        if not self.pending_restart or self.restart_in_progress:
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": "No pending restart to cancel or restart already in progress"
                    },
                    source="restart_manager",
                    reply_to=message.source
                )
            return
        
        # Cancel the pending restart
        reason = self.pending_restart["reason"]
        self.pending_restart = None
        
        # Announce cancellation
        await system_bus.publish(
            message_type="system.restart.cancelled",
            content={
                "reason": reason
            },
            source="restart_manager",
            priority=MessagePriority.HIGH
        )
        
        logger.info(f"Restart cancelled for reason: {reason}")
        
        # Reply if requested
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": True,
                    "message": "Restart cancelled"
                },
                source="restart_manager",
                reply_to=message.source
            )
    
    async def _schedule_restart(self, delay: float):
        """
        Schedule a restart after a delay.
        
        Args:
            delay: Delay in seconds before restart
        """
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay)
            
            # Check if restart was cancelled
            if not self.pending_restart:
                logger.info("Scheduled restart was cancelled")
                return
            
            # Perform the restart
            await self._perform_restart()
        
        except asyncio.CancelledError:
            # Task was cancelled
            logger.info("Restart scheduling task was cancelled")
        
        except Exception as e:
            logger.error(f"Error scheduling restart: {str(e)}", exc_info=True)
    
    async def _perform_restart(self):
        """Perform the system restart."""
        if not self.pending_restart:
            logger.warning("No pending restart to perform")
            return
        
        if self.restart_in_progress:
            logger.warning("Restart already in progress")
            return
        
        self.restart_in_progress = True
        restart_info = self.pending_restart
        
        try:
            logger.info(f"Performing system restart for reason: {restart_info['reason']}")
            
            # Announce imminent restart
            await system_bus.publish(
                message_type="system.restart.imminent",
                content={
                    "reason": restart_info["reason"],
                    "time_remaining": 10  # 10 seconds warning
                },
                source="restart_manager",
                priority=MessagePriority.CRITICAL
            )
            
            # Give components time to prepare
            await asyncio.sleep(5)
            
            # Create restart marker
            restart_info["shutdown_time"] = time.time()
            marker_path = os.path.join(self.state_dir, "restart_marker.json")
            with open(marker_path, 'w') as f:
                json.dump(restart_info, f, indent=2)
            
            # Announce final shutdown
            await system_bus.publish(
                message_type="system.shutdown",
                content={
                    "reason": "restart",
                    "restart_info": restart_info
                },
                source="restart_manager",
                priority=MessagePriority.CRITICAL
            )
            
            # Wait for components to shutdown
            await asyncio.sleep(5)
            
            # Spawn the restart process
            logger.info("Spawning restart process")
            restart_cmd = [
                self.python_executable,
                self.main_script,
                "--restart",
                f"--reason={restart_info['reason']}"
            ]
            
            # Use subprocess to start the new process
            subprocess.Popen(
                restart_cmd,
                cwd=self.system_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Exit the current process
            logger.info("Exiting for restart")
            sys.exit(0)
        
        except Exception as e:
            logger.error(f"Error performing restart: {str(e)}", exc_info=True)
            self.restart_in_progress = False
            self.pending_restart = None
            
            # Announce restart failure
            await system_bus.publish(
                message_type="system.restart.failed",
                content={
                    "reason": restart_info["reason"],
                    "error": str(e)
                },
                source="restart_manager",
                priority=MessagePriority.HIGH
            )