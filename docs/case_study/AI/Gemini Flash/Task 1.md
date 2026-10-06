1. `httpie/__main__.py`                                                                                                                                                                     
   └── `main()`                                                                                                                                                                             
       └── Calls `httpie.core.main()`                                                                                                                                                       
           │                                                                                                                                                                                
2. `httpie/core.py`                                                                                                                                                                         
   └── `main(args=sys.argv, env=Environment())`                                                                                                                                             
       └── `raw_main(parser=parser, main_program=program, args=args, env=env)`                                                                                                              
           ├── `decode_raw_args(args, env.stdin_encoding)`                                                                                                                                  
           ├── `httpie.plugins.manager.PluginManager.load_installed_plugins(directory=env.config.plugins_dir)`                                                                              
           │   ├── Accesses property `httpie.context.Environment.config`                                                                                                                    
           │   │   └── Initializes `httpie.config.Config(directory=self.config_dir)` & calls `Config.load()`                                                                                
           │   └── `PluginManager.iter_entry_points()` -> loads registered plugins into registry                                                                                            
           │                                                                                                                                                                                
           ├── `httpie.cli.argparser.HTTPieArgumentParser.parse_args(env, args, namespace)`                                                                                                 
           │   ├── `argparse.ArgumentParser.parse_known_args()`                                                                                                                             
           │   ├── `HTTPieArgumentParser._apply_no_options(no_options)`                                                                                                                     
           │   ├── `HTTPieArgumentParser._process_request_type()`                                                                                                                           
           │   ├── `HTTPieArgumentParser._process_download_options()`                                                                                                                       
           │   ├── `HTTPieArgumentParser._setup_standard_streams()`                                                                                                                         
           │   │   └── Configures `env.stdout`, `env.stderr`, `env.quiet`, etc.                                                                                                             
           │   ├── `HTTPieArgumentParser._process_output_options()`                                                                                                                         
           │   ├── `HTTPieArgumentParser._process_pretty_options()`                                                                                                                         
           │   ├── `HTTPieArgumentParser._process_format_options()`                                                                                                                         
           │   ├── `HTTPieArgumentParser._guess_method()`                                                                                                                                   
           │   ├── `HTTPieArgumentParser._parse_items()`                                                                                                                                    
           │   │   └── `httpie.cli.requestitems.RequestItems.from_args()` -> sets headers, data, params, files                                                                              
           │   ├── `HTTPieArgumentParser._process_url()`                                                                                                                                    
           │   ├── `HTTPieArgumentParser._process_auth()`                                                                                                                                   
           │   │   └── Obtains auth plugins from `PluginManager` / initialises credentials                                                                                                  
           │   ├── `HTTPieArgumentParser._process_ssl_cert()`                                                                                                                               
           │   └── (Optional) `_body_from_input()` or `_body_from_file()`                                                                                                                   
           │                                                                                                                                                                                
           └── Invokes `main_program` -> `httpie.core.program(args=parsed_args, env=env)`                                                                                                   
               ├── `httpie.output.models.ProcessingOptions.from_raw_args(args)`                                                                                                             
               ├── (Optional) Initializes `httpie.downloads.Downloader(env, output_file=args.output_file, resume=args.download_resume)`                                                     
               │   └── `Downloader.pre_request(args.headers)`                                                                                                                               
               │                                                                                                                                                                            
               ├── `httpie.client.collect_messages(env, args, request_body_read_callback)`                                                                                                  
               │   ├── (Optional) `httpie.sessions.get_httpie_session()` -> Initialises `httpie.sessions.Session`                                                                           
               │   ├── `httpie.client.make_request_kwargs(env, args, ...)`                                                                                                                  
               │   │   ├── `make_default_headers(args)`                                                                                                                                     
               │   │   ├── `finalize_headers(headers)`                                                                                                                                      
               │   │   └── `httpie.uploads.prepare_request_body()`                                                                                                                          
               │   ├── `httpie.client.make_send_kwargs(args)`                                                                                                                               
               │   ├── `httpie.client.make_send_kwargs_mergeable_from_env(args)`                                                                                                            
               │   │   └── (Optional) Instantiates `httpie.ssl_.HTTPieCertificate`                                                                                                          
               │   ├── `httpie.client.build_requests_session(verify, ssl_version, ciphers)`                                                                                                 
               │   │   ├── Instantiates `requests.Session()`                                                                                                                                
               │   │   ├── Mounts `httpie.adapters.HTTPieHTTPAdapter`                                                                                                                       
               │   │   └── Mounts `httpie.ssl_.HTTPieHTTPSAdapter`                                                                                                                          
               │   │                                                                                                                                                                        
               │   ├── Instantiates `requests.Request(**request_kwargs)`                                                                                                                    
               │   ├── `requests.Session.prepare_request(request)` -> creates `requests.PreparedRequest`                                                                                    
               │   ├── `httpie.client.transform_headers(request, prepared_request)`                                                                                                         
               │   ├── `yield prepared_request`                                                                                                                                             
               │   │                                                                                                                                                                        
               │   └── (Online execution loop):                                                                                                                                             
               │       ├── `requests.Session.send(prepared_request, ...)` -> creates `requests.Response`                                                                                    
               │       └── `yield response`                                                                                                                                                 
               │                                                                                                                                                                            
               └── Iterates over each `message` yielded by `collect_messages`:                                                                                                              
                   ├── `httpie.models.OutputOptions.from_message(message, args.output_options)`                                                                                             
                   │   ├── `httpie.models.infer_requests_message_kind(message)`                                                                                                             
                   │   │   └── Determines `RequestsMessageKind.REQUEST` or `RequestsMessageKind.RESPONSE`                                                                                   
                   │   └── Instantiates `httpie.models.OutputOptions`                                                                                                                       
                   │                                                                                                                                                                        
                   └── `httpie.output.writer.write_message(requests_message, env, output_options, processing_options)`                                                                      
                       └── Wraps the raw requests message into core HTTP model wrappers:                                                                                                    
                           ├── If `requests.PreparedRequest`:                                                                                                                               
                           │   └── Instantiates `httpie.models.HTTPRequest(orig=requests_message)` (subclass of `httpie.models.HTTPMessage`)                                                
                           └── If `requests.Response`:                                                                                                                                      
                               └── Instantiates `httpie.models.HTTPResponse(orig=requests_message)` (subclass of `httpie.models.HTTPMessage`)        